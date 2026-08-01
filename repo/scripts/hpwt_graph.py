"""hpwt_graph.py - LangGraph orchestration layer (spec 00 Layer 4).

Wires the already-built Layer-1 modules into the locked HPWT loop:

    propose -> kb_gauntlet -> confidence_gate --(conditional)--> [da_review] ->
    nick_approval -> dual_execute -> verify -> kb_update

Each node calls the real functions (risk_engine.score / aggregate_batch_risk,
role_routing.route, dispatch_design.check_dispatch_design, notify.notify_nick).
No formula, threshold, or routing rule is reimplemented here - this module is
orchestration only (spec 00 Layer 4).

Checkpointer: PostgresSaver against tazaos on n100 (confirmed working), with a
fail-closed fallback to local SqliteSaver. On connection failure at graph
startup the graph runs on sqlite, writes /home/taza/hpwt-graph/db-mode (same
shape as /var/lib/taza/llama-mode), and notifies Nick via ntfy. An automatic
recovery-retry timer is a follow-up, deliberately NOT built here.

Notifications (spec 06): nick_approval fires notify_nick(urgency='pause') for
Band 1 and (urgency='inform') for Band 2; Bands 3/4 pass through silently.
Band 1 ALWAYS blocks via the LangGraph human-in-the-loop interrupt regardless
of whether the notification went through (fail-closed). If the notification
failed, a durable pending-approval marker is written for the session-start
ritual to find.
"""

import atexit
import json
import re
from contextlib import ExitStack
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TypedDict

from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from dispatch_design import check_dispatch_design
from notify import notify_nick
from risk_engine import aggregate_batch_risk, band_of, score
from role_routing import route

# ---------------------------------------------------------------------------
# Constants (verified this session - see checkpoint + /etc/taza/ntfy.conf)
# ---------------------------------------------------------------------------

DB_ENV_PATH = Path("/home/taza/hpwt-graph/db.env")
FALLBACK_SQLITE = Path("/home/taza/hpwt-graph/fallback_checkpoints.db")
DB_MODE_FILE = Path("/home/taza/hpwt-graph/db-mode")
PENDING_DIR = Path("/home/taza/hpwt-graph/pending-approval")
DISPATCH_DIR = Path("/home/taza/hpwt-graph/dispatches")
KB_LOG = Path("/home/taza/hpwt-graph/kb-log.jsonl")

POSTGRES_HOST = "192.168.2.102"
POSTGRES_PORT = 5432
POSTGRES_DB = "tazaos"
POSTGRES_USER = "hpwt_graph"


def _primary_topic() -> str:
    """NTFY_TOPIC from taza-ntfy.conf - fixed per install, never chosen per-call."""
    for p in (Path("/etc/taza/ntfy.conf"), Path(__file__).parent / "taza-ntfy.conf"):
        try:
            for line in p.read_text().splitlines():
                if line.startswith("NTFY_TOPIC="):
                    return line.split("=", 1)[1].strip()
        except OSError:
            continue
    return "taza-ops"


PRIMARY_TOPIC = _primary_topic()

# Contexts entered at startup stay open for the process lifetime (the
# PostgresSaver / SqliteSaver from_conn_string generators yield a saver whose
# connection must stay alive for checkpoint reads/writes).
_STACK = ExitStack()
atexit.register(_STACK.close)


# ---------------------------------------------------------------------------
# State schema
# ---------------------------------------------------------------------------

class HPWTState(TypedDict, total=False):
    task: str                     # the Driver's proposal (required)
    s: int                        # severity 1..5 (elicited upstream of the graph)
    o: int                        # occurrence 1..5
    d: int                        # detection 1..5
    research_adjusted_o: int      # spec 01 re-score-after-research (optional)
    item_scores: list[float]      # per-item R values for ABR (defaults to [r])
    chained: bool
    tool_access: str              # aider | browser | both
    domain: str                   # generic | web | ...
    design: dict                  # check_dispatch_design() output
    risk: dict                    # score() output (final, re-scored)
    routing: dict                 # route() output
    gate: dict                    # confidence-gate decision record
    da_rounds: int
    da_disposition: str           # resolved | well_founded (external agents set)
    da_nature: str                # structural | epistemic_asymmetry
    da_mitigation: str | None
    da_result: dict
    force_nick_pause: bool        # spec 04 structural deadlock -> pause regardless of band
    verifier_flag: str | None     # spec 04 epistemic deadlock -> verifier must check
    notify_result: dict
    approval: Any                 # nick_approval interrupt resume value
    execution: dict
    verify: dict
    kb: dict


# ---------------------------------------------------------------------------
# Checkpointer selection with sqlite fallback (robustness addition 1)
# ---------------------------------------------------------------------------

def load_db_password(db_env: Path = DB_ENV_PATH) -> str:
    """HPWT_DB_PASSWORD from db.env - never hardcoded, never committed."""
    for line in db_env.read_text().splitlines():
        line = line.strip()
        if line.startswith("HPWT_DB_PASSWORD="):
            pw = line.split("=", 1)[1]
            if pw:
                return pw
    raise RuntimeError("no HPWT_DB_PASSWORD value in %s" % db_env)


def write_db_mode(mode: str, reason: str, needs_root_cause: int = 1,
                  path: Path = DB_MODE_FILE) -> Path:
    """Same shape as /var/lib/taza/llama-mode (llama-failover.sh write_state)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    content = (
        "mode=%s\n" % mode
        + "since=%s\n" % datetime.now(timezone.utc).isoformat()
        + "reason=%s\n" % reason
        + "needs_root_cause=%d\n" % (1 if needs_root_cause else 0)
    )
    path.write_text(content)
    path.chmod(0o644)
    return path


def _open_pg_saver(conn_string: str) -> PostgresSaver:
    cm = PostgresSaver.from_conn_string(conn_string)
    saver = _STACK.enter_context(cm)   # kept open for process lifetime
    saver.setup()                      # creates/verifies the 4 checkpoint tables
    return saver


def _open_sqlite_saver(path: Path) -> SqliteSaver:
    path.parent.mkdir(parents=True, exist_ok=True)
    cm = SqliteSaver.from_conn_string(str(path))  # plain path: sqlite3.connect() gets it verbatim
    return _STACK.enter_context(cm)


def select_checkpointer(db_env: Path = DB_ENV_PATH,
                        fallback_sqlite: Path = FALLBACK_SQLITE,
                        mode_file: Path = DB_MODE_FILE,
                        notify=notify_nick,
                        topic: str = PRIMARY_TOPIC) -> tuple:
    """PostgresSaver first; on ANY connection/setup failure fall back to
    local SqliteSaver, write the db-mode state file, and inform Nick.
    Returns (checkpointer, meta) - meta['mode'] is 'postgres' or
    'sqlite_fallback'."""
    try:
        pw = load_db_password(db_env)
        conn_string = ("postgresql://%s:%s@%s:%d/%s"
                       % (POSTGRES_USER, pw, POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB))
        saver = _open_pg_saver(conn_string)
        return saver, {"mode": "postgres", "conn": "%s:%d/%s" % (POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB)}
    except Exception as e:
        reason = "%s: %s" % (type(e).__name__, e)
        saver = _open_sqlite_saver(fallback_sqlite)
        write_db_mode("sqlite_fallback", reason, needs_root_cause=1, path=mode_file)
        try:
            notify(message="hpwt_graph checkpointer fell back to sqlite - %s" % reason,
                   urgency="inform", topic=topic)
        except Exception:
            pass  # a failed notification must never mask the fallback itself
        return saver, {"mode": "sqlite_fallback", "reason": reason, "path": str(fallback_sqlite)}


# ---------------------------------------------------------------------------
# Durable pending-approval marker (fail-closed notification handling)
# ---------------------------------------------------------------------------

def write_pending_marker(state: HPWTState, notify_result: dict,
                         pending_dir: Path | None = None) -> str:
    """Durable marker the session-start ritual can find: a blocked item whose
    pause notification did not go through. JSON file, chmod 600.
    pending_dir resolves at call time (default PENDING_DIR) so tests can patch
    the module global - a definition-time default would capture the original."""
    if pending_dir is None:
        pending_dir = PENDING_DIR
    pending_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    slug = re.sub(r"[^A-Za-z0-9]+", "-", (state.get("task") or "task")[:40]).strip("-") or "task"
    path = pending_dir / ("%s-%s.json" % (ts, slug))
    payload = {
        "blocked": True,
        "node": "nick_approval",
        "task": state.get("task"),
        "risk": state.get("risk"),
        "notify_failed": notify_result,
        "required_action": "nick_approval",
        "created_at": ts,
    }
    path.write_text(json.dumps(payload, indent=2))
    path.chmod(0o600)
    return str(path)


# ---------------------------------------------------------------------------
# Nodes (each calls the real Layer-1 functions; no logic reimplementation)
# ---------------------------------------------------------------------------

def propose(state: HPWTState) -> dict:
    """Driver's proposal enters the graph. Runs the spec 05 dispatch-design
    checklist gate on it via the real check_dispatch_design()."""
    task = state.get("task")
    if not task or not str(task).strip():
        raise ValueError("propose: task is required")
    design = check_dispatch_design(
        scope_ok=bool(state.get("design_scope_ok", True)),
        sequencing_ok=bool(state.get("design_sequencing_ok", True)),
        efficiency_ok=bool(state.get("design_efficiency_ok", True)),
        unambiguous_ok=bool(state.get("design_unambiguous_ok", True)),
    )
    return {"task": str(task).strip(), "design": design}


def kb_gauntlet(state: HPWTState) -> dict:
    """KB knowledge check. In code: S/O/D must be present and in range (score()
    raises, never clamps - spec 01), and if research produced an updated O the
    final band reads the RE-SCORED value (spec 01 re-score rule), never the
    provisional one."""
    s, o, d = state.get("s"), state.get("o"), state.get("d")
    if None in (s, o, d):
        raise ValueError("kb_gauntlet: S/O/D missing - Driver must elicit them before the gate (spec 01)")
    final_o = state.get("research_adjusted_o", o)
    risk = score(s, final_o, d)  # real function - single source of truth for R/band
    return {"risk": risk,
            "kb_check": {"passed": True,
                         "score_source": "re-scored" if final_o != o else "as-elicited"}}


def confidence_gate(state: HPWTState) -> dict:
    """Escalation Gate (spec 01): compute R (done in kb_gauntlet), assign the
    band, call route() for ABR/DA/executor decisions. The band's block/proceed
    semantics are applied by the conditional edge and by nick_approval."""
    risk = state.get("risk") or {}
    item_scores = state.get("item_scores") or [risk.get("r", 0.0)]
    routing = route(item_scores=item_scores,
                    chained=bool(state.get("chained", False)),
                    tool_access=state.get("tool_access", "aider"))
    if not routing.get("proceed", False):
        # ABR ceiling exceeded - deterministic reject (spec 02/03). No execution.
        return {"routing": routing, "gate": {"action": "block_abr_ceiling",
                                             "reason": routing.get("reason", "unknown")}}
    band = risk.get("band")
    action = {1: "pause_for_nick", 2: "inform_proceed"}.get(band, "proceed")
    return {"routing": routing,
            "gate": {"action": action, "band": band, "color": risk.get("color")}}


def gate_router(state: HPWTState) -> str:
    """Conditional edge out of confidence_gate (spec 00 Layer 4)."""
    if not state.get("routing", {}).get("proceed", True):
        return "rejected"
    if state.get("routing", {}).get("da_required"):
        return "da_review"
    return "nick_approval"


def da_review(state: HPWTState) -> dict:
    """One DA review pass (spec 04 Loop 1). The Socratic concern discussion is
    an agent activity carried in state; this node applies the deterministic
    round-cap and escalation rules. Structural deadlock -> pause-for-Nick
    (regardless of band); epistemic deadlock -> forced decision + verifier flag
    + inform-level ntfy. Both fire ntfy per spec 04's logged-deadlock rule."""
    rounds = int(state.get("da_rounds", 0)) + 1
    disposition = state.get("da_disposition", "resolved")
    if disposition == "resolved":
        return {"da_rounds": rounds,
                "da_result": {"status": "resolved", "rounds_used": rounds}}
    if rounds >= 2:
        nature = state.get("da_nature", "structural")  # spec 04: unclassified defaults structural
        deadlock = {"status": "deadlock", "rounds_used": rounds, "nature": nature,
                    "mitigation_attempted": state.get("da_mitigation")}
        try:
            notify_nick(
                message=("[hpwt_graph] DA deadlock (round %d, %s) on: %s"
                         % (rounds, nature, (state.get("task") or "")[:200])),
                urgency="pause" if nature == "structural" else "inform",
                topic=PRIMARY_TOPIC)
        except Exception:
            pass  # ntfy is a side effect; gate semantics below still apply
        extra = {"force_nick_pause": True} if nature == "structural" \
            else {"verifier_flag": "da_deadlock_epistemic"}
        return {"da_rounds": rounds, "da_result": deadlock, **extra}
    return {"da_rounds": rounds,
            "da_result": {"status": "mitigating", "rounds_used": rounds,
                          "mitigation_attempted": state.get("da_mitigation")}}


def _escalation_message(state: HPWTState, urgency: str) -> str:
    risk = state.get("risk") or {}
    return ("[hpwt_graph] %s - band %s (%s) R=%s - task: %s"
            % (urgency.upper(), risk.get("band"), risk.get("color"),
               risk.get("r"), (state.get("task") or "(untitled)")[:200]))


def nick_approval(state: HPWTState) -> dict:
    """Nick's human-in-the-loop gate (spec 06). Band 1: notify_nick('pause')
    then ALWAYS block via the LangGraph interrupt - the notification is a side
    effect, never a precondition of the block (fail-closed). If the notification
    failed, write a durable pending-approval marker. Band 2: notify 'inform'
    and proceed. Bands 3/4: pass through silently (spec 01)."""
    risk = state.get("risk") or {}
    band = risk.get("band")
    force_pause = bool(state.get("force_nick_pause", False))
    band1 = force_pause or band == 1
    if band not in (1, 2) and not force_pause:
        return {"approval": "band34_proceed",
                "notify_result": {"sent": True, "channel": "none_needed"}}
    urgency = "pause" if band1 else "inform"
    result = notify_nick(message=_escalation_message(state, urgency),
                         urgency=urgency, topic=PRIMARY_TOPIC)
    if band1:
        if not result.get("sent", False):
            marker = write_pending_marker(state, result)
            result = dict(result)
            result["pending_marker"] = marker
        # Block UNCONDITIONALLY - spec 06: Band 1 pauses until Nick acts,
        # regardless of whether the notification went through.
        decision = interrupt({
            "node": "nick_approval",
            "band": band,
            "color": risk.get("color"),
            "r": risk.get("r"),
            "task": state.get("task"),
            "notification": result,
        })
        return {"approval": decision, "notify_result": result}
    return {"approval": "band2_proceed", "notify_result": result}


def dual_execute(state: HPWTState) -> dict:
    """Execution dispatch (spec 00 Layer 4): consults route() for the executor
    subtypes; parallel branches when both are needed. Emits a durable dispatch
    artifact (spec 06: artifact + link for anything meant for another system)."""
    item_scores = state.get("item_scores") or [state.get("risk", {}).get("r", 0.0)]
    routing = route(item_scores=item_scores,
                    chained=bool(state.get("chained", False)),
                    tool_access=state.get("tool_access", "aider"))
    subtypes = routing.get("executor_subtypes", ["Executor-Aider"])
    record = {
        "task": state.get("task"),
        "executor_subtypes": subtypes,
        "parallel_branches": len(subtypes) > 1,
        "risk": state.get("risk"),
        "design": state.get("design"),
        "da_result": state.get("da_result"),
        "approval": state.get("approval"),
        "verifier_flag": state.get("verifier_flag"),
    }
    DISPATCH_DIR.mkdir(parents=True, exist_ok=True)
    path = DISPATCH_DIR / ("%s-dispatch.json" % datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    path.write_text(json.dumps(record, indent=2))
    path.chmod(0o600)
    return {"execution": {"artifact": str(path), "executor_subtypes": subtypes,
                          "parallel_branches": len(subtypes) > 1}}


def verify(state: HPWTState) -> dict:
    """Deterministic structural verification (spec 06/08): an execution claim
    with no linked artifact is unverified; a web/browser completion claim with
    no VNC/screenshot capture artifact is unverified, full stop. Verifier
    failure on the web domain fires ntfy (spec 06's human-eyeball fallback)."""
    execution = state.get("execution") or {}
    checks = []
    if not execution.get("artifact"):
        checks.append("no execution artifact")
    if state.get("domain") == "web" and state.get("tool_access") == "browser" \
            and not execution.get("capture_artifact"):
        checks.append("web task: no VNC/screenshot capture artifact")
    passed = not checks
    result = {"passed": passed, "checks": checks, "domain": state.get("domain", "generic")}
    if not passed and state.get("domain") == "web":
        try:
            notify_nick(message="[hpwt_graph] Verifier FAILED on web domain: %s" % checks,
                        urgency="inform", topic=PRIMARY_TOPIC)
        except Exception:
            pass
    return {"verify": result}


def kb_update(state: HPWTState) -> dict:
    """KB write-back (spec 00 Layer 2/3): appends the full decision record to
    the local durable KB log. (Notion KB sync is a follow-up - not part of this
    dispatch; the record here is the evidence base that sync would consume.)"""
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "task": state.get("task"),
        "risk": state.get("risk"),
        "abr": state.get("routing", {}).get("abr"),
        "outcome": state.get("routing", {}).get("outcome"),
        "gate": state.get("gate"),
        "design": state.get("design"),
        "da": state.get("da_result"),
        "approval": state.get("approval"),
        "execution": state.get("execution"),
        "verify": state.get("verify"),
    }
    KB_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(KB_LOG, "a") as f:
        f.write(json.dumps(record) + "\n")
    return {"kb": {"logged": str(KB_LOG), "ts": record["ts"]}}


# ---------------------------------------------------------------------------
# Graph assembly (spec 00 Layer 4 shape, exactly)
# ---------------------------------------------------------------------------

def build_graph(checkpointer=None):
    """Compile the HPWT state graph. checkpointer=None -> select_checkpointer()
    (PostgresSaver with sqlite fallback)."""
    if checkpointer is None:
        checkpointer, _meta = select_checkpointer()
    builder = StateGraph(HPWTState)
    builder.add_node("propose", propose)
    builder.add_node("kb_gauntlet", kb_gauntlet)
    builder.add_node("confidence_gate", confidence_gate)
    builder.add_node("da_review", da_review)
    builder.add_node("nick_approval", nick_approval)
    builder.add_node("dual_execute", dual_execute)
    builder.add_node("verify", verify)
    builder.add_node("kb_update", kb_update)
    builder.add_edge(START, "propose")
    builder.add_edge("propose", "kb_gauntlet")
    builder.add_edge("kb_gauntlet", "confidence_gate")
    builder.add_conditional_edges(
        "confidence_gate", gate_router,
        {"da_review": "da_review", "nick_approval": "nick_approval", "rejected": END})
    builder.add_edge("da_review", "nick_approval")
    builder.add_edge("nick_approval", "dual_execute")
    builder.add_edge("dual_execute", "verify")
    builder.add_edge("verify", "kb_update")
    builder.add_edge("kb_update", END)
    return builder.compile(checkpointer=checkpointer)


# Names re-exported so tests can assert against the real functions and so the
# module advertises exactly what the spec's build order expects.
__all__ = [
    "HPWTState", "PRIMARY_TOPIC", "select_checkpointer", "build_graph",
    "propose", "kb_gauntlet", "confidence_gate", "gate_router", "da_review",
    "nick_approval", "dual_execute", "verify", "kb_update",
    "score", "aggregate_batch_risk", "band_of", "route", "check_dispatch_design", "notify_nick",
]
