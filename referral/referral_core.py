"""
referral_core.py — Taza Spatula Referral Chain: identity, integrity, influence.

Pure-ish logic layer shared by the web app and the issuance/burn tooling:

  * issuance_id  — short, human-quotable, URL-safe key burned into each QR.
  * chain_hash   — HMAC pedigree hash. Pre-registered at engrave time so a
                   photocopied/screenshotted QR can't spoof a valid record.
  * leaderboard  — annual dollar ranking (direct or full downstream subtree).
  * influence    — network reach per party (subtree size, depth, dollars).

The secret used for chain_hash lives OUTSIDE this file — env var
TAZA_REFERRAL_SECRET on the N100. Without it you can read a QR but you cannot
forge a new valid (issuance_id, chain_hash) pair.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from dataclasses import dataclass

import psycopg2
import psycopg2.extras

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

# Crockford base32 alphabet (no I, L, O, U — unambiguous when read off wood).
_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
ISSUANCE_PREFIX = "TZ-"

DB_DSN = os.environ.get(
    "TAZA_DB_DSN",
    "dbname=tazaos user=taza host=127.0.0.1 port=5432",
)


def _secret() -> bytes:
    s = os.environ.get("TAZA_REFERRAL_SECRET")
    if not s:
        raise RuntimeError(
            "TAZA_REFERRAL_SECRET is not set. Generate one once with "
            "`openssl rand -hex 32` and store it in the systemd unit / .env — "
            "it must stay identical for the life of the program or every "
            "already-burned QR becomes unverifiable."
        )
    return s.encode("utf-8")


def get_conn():
    """Open a psycopg2 connection. Caller manages the transaction."""
    return psycopg2.connect(DB_DSN)


# ---------------------------------------------------------------------------
# Issuance IDs
# ---------------------------------------------------------------------------

def new_issuance_id(n: int = 6) -> str:
    """A fresh short code like TZ-7F3K9Q. ~1e9 space for n=6 — collisions are
    checked against the DB at insert time, so this only needs to be sparse."""
    body = "".join(secrets.choice(_ALPHABET) for _ in range(n))
    return f"{ISSUANCE_PREFIX}{body}"


# ---------------------------------------------------------------------------
# Chain hashing (integrity / anti-forgery)
# ---------------------------------------------------------------------------

def compute_chain_hash(issuance_id: str, parent_chain_hash: str | None) -> str:
    """Deterministic HMAC over this spatula's id and its parent's chain hash.

    Because it chains the parent hash in, the value binds the whole ancestry:
    change any ancestor and every descendant hash changes. We keep only the
    first 16 hex chars in the QR payload (64 bits) — plenty to make forgery a
    brute-force problem, while the DB row is the real authority.
    """
    parent = parent_chain_hash or "ROOT"
    msg = f"{issuance_id}|{parent}".encode("utf-8")
    return hmac.new(_secret(), msg, hashlib.sha256).hexdigest()


def verify_chain_hash(issuance_id: str, parent_chain_hash: str | None,
                      presented: str) -> bool:
    expected = compute_chain_hash(issuance_id, parent_chain_hash)
    # Constant-time compare; tolerate the truncated form stored in the QR.
    presented = (presented or "").strip().lower()
    return hmac.compare_digest(expected[: len(presented)], presented) and len(presented) >= 16


# ---------------------------------------------------------------------------
# QR payload
# ---------------------------------------------------------------------------

def scan_url(base_url: str, issuance_id: str, chain_hash: str) -> str:
    """The URL the QR actually encodes. Compact: id + truncated chain hash.
    The DB holds the pedigree tree; this is only the key that unlocks it."""
    base = base_url.rstrip("/")
    return f"{base}/scan?s={issuance_id}&c={chain_hash[:16]}"


# ---------------------------------------------------------------------------
# Issuance — create a spatula row (called at engrave time, before the burn)
# ---------------------------------------------------------------------------

@dataclass
class Issued:
    issuance_id: str
    chain_hash: str
    depth: int
    parent_issuance_id: str | None


def issue_spatula(conn, parent_issuance_id: str | None = None,
                  owner_id: str | None = None, notes: str | None = None) -> Issued:
    """Pre-register a new spatula and return its identity for the burn.

    If parent_issuance_id is given, this spatula extends that pedigree chain.
    """
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        parent_hash = None
        depth = 0
        if parent_issuance_id:
            cur.execute(
                "SELECT chain_hash, depth FROM referral.spatula WHERE issuance_id = %s",
                (parent_issuance_id,),
            )
            row = cur.fetchone()
            if not row:
                raise ValueError(f"parent spatula {parent_issuance_id} not found")
            parent_hash = row["chain_hash"]
            depth = row["depth"] + 1

        # Retry a handful of times on the (rare) short-code collision.
        for _ in range(8):
            iid = new_issuance_id()
            ch = compute_chain_hash(iid, parent_hash)
            try:
                cur.execute(
                    """INSERT INTO referral.spatula
                         (issuance_id, owner_id, parent_issuance_id, chain_hash, depth, status, notes)
                       VALUES (%s, %s, %s, %s, %s, 'burned', %s)""",
                    (iid, owner_id, parent_issuance_id, ch, depth, notes),
                )
                conn.commit()
                return Issued(iid, ch, depth, parent_issuance_id)
            except psycopg2.errors.UniqueViolation:
                conn.rollback()
                continue
        raise RuntimeError("could not allocate a unique issuance_id after 8 tries")


# ---------------------------------------------------------------------------
# Leaderboard + influence (recursive over the referral tree)
# ---------------------------------------------------------------------------

# Full downstream subtree dollars per party for the contest year, plus reach.
# influence_score is a simple, explainable blend: dollars dominate, with a small
# bonus for breadth (people reached) and depth (chain length). Tunable later.
_SUBTREE_SQL = """
WITH RECURSIVE
cfg AS (SELECT contest_year, prize_metric FROM referral.prize_config),
-- descendants(root, node): every party reachable downstream of root via referred_by.
descendants AS (
    SELECT p.party_id AS root, p.party_id AS node, 0 AS gen
    FROM referral.party p
    UNION ALL
    SELECT d.root, c.party_id, d.gen + 1
    FROM descendants d
    JOIN referral.party c ON c.referred_by = d.node
),
year_booking AS (
    SELECT customer_id, net_amount
    FROM referral.booking, cfg
    WHERE date_part('year', booked_at) = cfg.contest_year
)
SELECT
    r.party_id                                             AS referrer_id,
    r.display_name                                         AS referrer_name,
    -- subtree dollars: bookings by anyone downstream (excluding the root themselves)
    coalesce(sum(yb.net_amount) FILTER (WHERE d.node <> r.party_id), 0) AS subtree_dollars,
    count(DISTINCT d.node) FILTER (WHERE d.node <> r.party_id)          AS reach,
    coalesce(max(d.gen), 0)                                             AS max_depth
FROM referral.party r
JOIN descendants d       ON d.root = r.party_id
LEFT JOIN year_booking yb ON yb.customer_id = d.node
GROUP BY r.party_id, r.display_name
"""


def leaderboard(conn, limit: int = 25) -> list[dict]:
    """Ranked contest standings. Honors prize_config.prize_metric for the rank
    dollar figure, but always returns both direct and subtree numbers so the UI
    can show the full story."""
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT contest_year, prize_metric, prize_label FROM referral.prize_config")
        cfg = cur.fetchone()

        cur.execute(_SUBTREE_SQL)
        subtree = {r["referrer_id"]: r for r in cur.fetchall()}

        cur.execute("SELECT referrer_id, direct_dollars, direct_referrals FROM referral.v_direct_dollars")
        direct = {r["referrer_id"]: r for r in cur.fetchall()}

    rows = []
    for pid, s in subtree.items():
        d = direct.get(pid, {})
        direct_dollars = float(d.get("direct_dollars") or 0)
        subtree_dollars = float(s["subtree_dollars"] or 0)
        reach = int(s["reach"] or 0)
        depth = int(s["max_depth"] or 0)
        rank_dollars = subtree_dollars if cfg["prize_metric"] == "subtree" else direct_dollars
        influence_score = round(rank_dollars + 15 * reach + 25 * depth, 2)
        rows.append({
            "referrer_id": pid,
            "referrer_name": s["referrer_name"],
            "direct_dollars": round(direct_dollars, 2),
            "direct_referrals": int(d.get("direct_referrals") or 0),
            "subtree_dollars": round(subtree_dollars, 2),
            "reach": reach,
            "max_depth": depth,
            "rank_dollars": round(rank_dollars, 2),
            "influence_score": influence_score,
        })

    # Drop parties with no activity at all, sort by the contest metric.
    rows = [r for r in rows if r["rank_dollars"] > 0 or r["reach"] > 0]
    rows.sort(key=lambda r: (r["rank_dollars"], r["reach"]), reverse=True)
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    return {
        "contest_year": cfg["contest_year"],
        "prize_metric": cfg["prize_metric"],
        "prize_label": cfg["prize_label"],
        "standings": rows[:limit],
    }


def pedigree(conn, issuance_id: str) -> list[dict]:
    """Ancestry chain for a spatula, root-first — powers 'referred by Maria T.'."""
    sql = """
    WITH RECURSIVE up AS (
        SELECT s.issuance_id, s.parent_issuance_id, s.owner_id, s.depth
        FROM referral.spatula s WHERE s.issuance_id = %s
        UNION ALL
        SELECT p.issuance_id, p.parent_issuance_id, p.owner_id, p.depth
        FROM referral.spatula p
        JOIN up ON up.parent_issuance_id = p.issuance_id
    )
    SELECT up.issuance_id, up.depth, party.display_name
    FROM up LEFT JOIN referral.party party ON party.party_id = up.owner_id
    ORDER BY up.depth ASC;
    """
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, (issuance_id,))
        return cur.fetchall()
