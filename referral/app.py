#!/usr/bin/env python3
"""
app.py — Taza Spatula Referral service (Flask). Runs on the N100, port 9002.

Routes (phone-friendly, no install — staff scans the QR, opens this page):
  GET  /health                 liveness for the watcher
  GET  /scan?s=<id>&c=<hash>    verify a spatula QR; show pedigree + 10%-off token
  POST /redeem                  staff confirms a booking -> records $ + discount
  POST /issue                   register a NEW spatula (returns QR PNG to burn)
  GET  /leaderboard             annual standings ($ + influence); prize = party for 8
  GET  /network                 who-knows-who edges (JSON) for influence analysis

The QR only carries (issuance_id, truncated chain_hash). The DB is the authority;
a photocopied QR fails verification because its (id, hash) pair must match a
pre-registered row AND recompute correctly under the server secret.
"""

from __future__ import annotations

import io
import os

from flask import Flask, request, jsonify, render_template_string, send_file

import referral_core as core
from qrgen import qr_panel

app = Flask(__name__)
BASE_URL = os.environ.get("TAZA_REFERRAL_BASE_URL", "http://192.168.2.102:9002")

# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    try:
        with core.get_conn() as conn, conn.cursor() as cur:
            cur.execute("SELECT 1 FROM referral.prize_config LIMIT 1")
            cur.fetchone()
        return jsonify(status="ok"), 200
    except Exception as e:  # noqa: BLE001
        return jsonify(status="error", detail=str(e)), 500


# ---------------------------------------------------------------------------
# Scan — the customer/staff-facing verification page
# ---------------------------------------------------------------------------

_SCAN_HTML = """
<!doctype html><meta name=viewport content="width=device-width,initial-scale=1">
<title>Taza Referral</title>
<style>body{font-family:system-ui;margin:0;background:#1a1a1a;color:#eee;padding:1.2rem}
.card{max-width:520px;margin:auto;background:#242424;border-radius:14px;padding:1.4rem}
.ok{color:#7bd88f}.bad{color:#ff6b6b}.gold{color:#c7a84b}
h1{font-size:1.4rem}.big{font-size:2rem;font-weight:700}
.ped{opacity:.85;font-size:.95rem;line-height:1.5}
button{background:#5b8ab5;color:#fff;border:0;border-radius:10px;padding:.8rem 1.1rem;font-size:1rem}</style>
<div class=card>
{% if valid %}
  <h1 class=ok>✓ Genuine Taza spatula</h1>
  <p class=big class=gold>10% off your booking</p>
  <p>Spatula <b>{{ iid }}</b>{% if owner %} · gifted to <b>{{ owner }}</b>{% endif %}</p>
  {% if pedigree %}<p class=ped>Referral chain:<br>
    {% for step in pedigree %}{{ '→ ' if not loop.first }}{{ step.display_name or 'Taza' }}{% endfor %}
  </p>{% endif %}
  <form method=post action=/redeem>
    <input type=hidden name=s value="{{ iid }}">
    <p>Booking value ($): <input name=amount type=number step=0.01 required></p>
    <p>New customer name: <input name=customer required></p>
    <button>Apply 10% &amp; record referral</button>
  </form>
{% else %}
  <h1 class=bad>✗ Could not verify</h1>
  <p>{{ reason }}</p>
  <p class=ped>A screenshot or photocopy won't verify — each spatula's code is
  pre-registered when it's burned. Ask the guest to present the physical spatula.</p>
{% endif %}
</div>
"""


@app.get("/scan")
def scan():
    iid = (request.args.get("s") or "").strip()
    presented = (request.args.get("c") or "").strip()
    if not iid:
        return render_template_string(_SCAN_HTML, valid=False, reason="No spatula id in QR.")
    with core.get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT s.parent_issuance_id, s.status, p.display_name "
            "FROM referral.spatula s LEFT JOIN referral.party p ON p.party_id=s.owner_id "
            "WHERE s.issuance_id=%s", (iid,))
        row = cur.fetchone()
        if not row:
            return render_template_string(_SCAN_HTML, valid=False, iid=iid,
                                          reason="Unknown spatula id — not in the issuance registry.")
        parent_iid, status, owner = row
        parent_hash = None
        if parent_iid:
            cur.execute("SELECT chain_hash FROM referral.spatula WHERE issuance_id=%s", (parent_iid,))
            r = cur.fetchone()
            parent_hash = r[0] if r else None
        if not core.verify_chain_hash(iid, parent_hash, presented):
            return render_template_string(_SCAN_HTML, valid=False, iid=iid,
                                          reason="Chain hash mismatch — possible forgery.")
        if status == "void":
            return render_template_string(_SCAN_HTML, valid=False, iid=iid,
                                          reason="This spatula was voided.")
        ped = core.pedigree(conn, iid)
    return render_template_string(_SCAN_HTML, valid=True, iid=iid, owner=owner, pedigree=ped)


# ---------------------------------------------------------------------------
# Redeem — record the booking + apply the discount, extend the chain
# ---------------------------------------------------------------------------

@app.post("/redeem")
def redeem():
    iid = (request.form.get("s") or "").strip()
    amount = request.form.get("amount", type=float)
    customer = (request.form.get("customer") or "").strip()
    if not (iid and amount and customer):
        return jsonify(error="s, amount, customer required"), 400
    with core.get_conn() as conn, conn.cursor() as cur:
        # The referred friend becomes a new party, referred_by the spatula's owner.
        cur.execute("SELECT owner_id FROM referral.spatula WHERE issuance_id=%s", (iid,))
        row = cur.fetchone()
        if not row:
            return jsonify(error="unknown spatula"), 404
        referrer_id = row[0]
        cur.execute(
            "INSERT INTO referral.party (display_name, referred_by) VALUES (%s,%s) RETURNING party_id",
            (customer, referrer_id))
        customer_id = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO referral.booking (customer_id, via_issuance_id, gross_amount) "
            "VALUES (%s,%s,%s) RETURNING net_amount", (customer_id, iid, amount))
        net = cur.fetchone()[0]
        cur.execute("UPDATE referral.spatula SET status='redeemed', redeemed_at=now() "
                    "WHERE issuance_id=%s AND status!='redeemed'", (iid,))
        # Seed the friendship edge (referrer knows the new customer).
        if referrer_id:
            a, b = sorted([str(referrer_id), str(customer_id)])
            cur.execute("INSERT INTO referral.knows_edge (party_a,party_b,relationship,source) "
                        "VALUES (%s,%s,'referred','referral') ON CONFLICT DO NOTHING", (a, b))
        conn.commit()
    return jsonify(ok=True, customer_id=str(customer_id), net_charged=float(net),
                   discount_applied="10%")


# ---------------------------------------------------------------------------
# Issue — register a new spatula and return its burnable QR PNG
# ---------------------------------------------------------------------------

@app.post("/issue")
def issue():
    parent = (request.form.get("parent") or "").strip() or None
    owner = (request.form.get("owner_id") or "").strip() or None
    caption = request.form.get("caption") or "Refer a friend - 10% off"
    with core.get_conn() as conn:
        issued = core.issue_spatula(conn, parent_issuance_id=parent, owner_id=owner)
    url = core.scan_url(BASE_URL, issued.issuance_id, issued.chain_hash)
    if request.args.get("format") == "png":
        buf = io.BytesIO()
        qr_panel(url, caption=caption).save(buf, format="PNG")
        buf.seek(0)
        return send_file(buf, mimetype="image/png",
                         download_name=f"{issued.issuance_id}.png")
    return jsonify(issuance_id=issued.issuance_id, chain_hash=issued.chain_hash,
                   depth=issued.depth, qr_url=url,
                   png=f"{BASE_URL}/issue?format=png (POST same params)")


# ---------------------------------------------------------------------------
# Leaderboard + network
# ---------------------------------------------------------------------------

_LB_HTML = """
<!doctype html><meta name=viewport content="width=device-width,initial-scale=1">
<title>Taza Referral Leaderboard {{ lb.contest_year }}</title>
<style>body{font-family:system-ui;background:#1a1a1a;color:#eee;padding:1.2rem}
table{border-collapse:collapse;width:100%;max-width:760px}
th,td{padding:.5rem .6rem;border-bottom:1px solid #333;text-align:left}
.gold{color:#c7a84b}.win{background:#2a2618}</style>
<h1 class=gold>🏆 {{ lb.contest_year }} Referral Leaderboard</h1>
<p>Prize: <b>{{ lb.prize_label }}</b> — ranked by
  {{ 'full downstream network dollars' if lb.prize_metric=='subtree' else 'direct-referral dollars' }}.</p>
<table><tr><th>#</th><th>Referrer</th><th>Contest $</th><th>Direct $</th>
<th>Network $</th><th>Reach</th><th>Depth</th><th>Influence</th></tr>
{% for r in lb.standings %}
<tr class="{{ 'win' if loop.first }}"><td>{{ r.rank }}</td><td>{{ r.referrer_name }}</td>
<td class=gold>${{ '%.2f'|format(r.rank_dollars) }}</td>
<td>${{ '%.2f'|format(r.direct_dollars) }}</td>
<td>${{ '%.2f'|format(r.subtree_dollars) }}</td>
<td>{{ r.reach }}</td><td>{{ r.max_depth }}</td><td>{{ r.influence_score }}</td></tr>
{% endfor %}
</table>
{% if not lb.standings %}<p>No referrals booked yet this year.</p>{% endif %}
"""


@app.get("/leaderboard")
def leaderboard():
    with core.get_conn() as conn:
        lb = core.leaderboard(conn)
    if request.args.get("format") == "json":
        return jsonify(lb)
    return render_template_string(_LB_HTML, lb=lb)


@app.get("/network")
def network():
    """Who-knows-who graph as JSON — nodes + edges for influence analysis."""
    with core.get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT party_id, display_name, referred_by FROM referral.party")
        nodes = [{"id": str(a), "name": b, "referred_by": str(c) if c else None}
                 for a, b, c in cur.fetchall()]
        cur.execute("SELECT party_a, party_b, relationship, weight FROM referral.knows_edge")
        edges = [{"a": str(a), "b": str(b), "rel": r, "weight": float(w)}
                 for a, b, r, w in cur.fetchall()]
    return jsonify(nodes=nodes, edges=edges)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("TAZA_REFERRAL_PORT", "9002")))
