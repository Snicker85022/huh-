# Domain Policies

No new mechanisms here. Each section applies the Risk Engine (01), Batch/Role Routing
(02, 03), or Dispatch Design (05) to one domain's decision shape. If a domain seems to
need new math, it belongs in a different file.

---

## Design Decisions

Governs whether a proposed change locks in (or reopens) architecture. Two triggers:

**A. New evidence supersedes a locked decision.**
```
1. New evidence found (e.g. a previously-rejected option retested and now works)
2. Run through Risk Engine + Escalation Gate
   - Reopening a lock is inherently high-Severity; expect Band 1-2 nearly always
3. Nick approves the change?
   - No  -> decision stays locked, no change
   - Yes -> mark superseded in decision_log, log new decision, LINK old and new
            decision_id (never silently overwrite)
```
Example: INFRA-005 (Cloudflare Tunnel) marked "permanently removed" 2026-06-28, then
superseded 2026-07-29 after Nick retested and approved it. Old entry preserved and
marked superseded, not deleted; confidence reset to reflect fresh (not battle-tested)
evidence.

**B. Schedule surplus enables scope pull-forward.**
```
1. Is core v1.0 ahead of schedule?
   - No  -> stay in scope, continue v1.0 as planned
   - Yes -> select the highest-value v1.x feature that best fits right now
2. Run the selected feature through Risk Engine + Dispatch Design -- same gates as
   any new work, no shortcut for being "ahead of schedule"
3. Add to active scope, log as a NEW decision_log entry (status='proposed' then
   'locked') -- not a supersede, don't link to an old decision_id
```

### `decision_log` schema (Postgres, per locked migration plan)

| Column | Notes |
|---|---|
| `decision_id` | e.g. `INFRA-006` |
| `title` | |
| `rationale` | |
| `decided_by` | nick / deepseek / claude-chat |
| `status` | `locked` / `proposed` / `superseded` |
| `supersedes` | nullable FK to another `decision_id`, only set for trigger A |
| `created_at` | |

---

## Hardware

**Evaluation objective function.** Any hardware candidate (purchase, upgrade, reuse):
```
objective = (usefulness + robustness) / cost
```
Never matched to a locked SKU.

**Conditional-heuristic gate.** If the plan assumes a hardware pairing/heuristic (e.g.
"attention on GPU, experts on CPU"), check the gating precondition (e.g. native
flash-attention support) before relying on it. Example: an AMD MI50 lacked
flash-attention hardware units; the unconditional version of this heuristic would have
assigned it the exact job it was worst at despite winning on raw memory bandwidth.

**Fact freshness.** Physical hardware specs are durable - recheck only on scope change,
never on a timer.

---

## Configuration

**Permission expansion gate.** Adding a binary to the passwordless sudoers allowlist:
score severity by blast radius, run through the Risk Engine. If approved, verify as
landed (`sudo -l` actually shows it) - a dispatch reporting `status=complete` is not
itself evidence; see 07.

**Configuration drift check.** Before relying on an assumed config state, verify
against live state, not documentation.
```python
def check_config_assumption(assumed_state, live_state_checker) -> dict:
    actual = live_state_checker()
    if actual == assumed_state:
        return {"proceed": True}
    update_kb(actual)  # close the drift immediately, don't just note the mismatch
    return {"proceed": False, "actual_state": actual}
```
Example: a service's crash-restart policy was assumed configured at initial systemd
unit creation but never was - caused a silent, permanent outage, found only during an
unrelated audit.

---

## Software & AI Models

Config, code, system details, APIs, model specifics live in the git repo
(`kb/software/`), never hardcoded in the Risk Engine module - concrete instance of the
layering principle from 00.

**Commit-backed verification.** A software/API/model-state claim must be backed by an
actual git commit, not narrative or memory:
```python
def verify_software_claim(claim, repo) -> dict:
    commit = repo.find_supporting_commit(claim)
    if commit:
        return {"verified": True, "commit": commit.sha}
    actual = repo.check_live_state(claim.target)  # git log/diff directly
    document_in_kb(actual, path="kb/software/")     # never in risk_engine.py
    return {"verified": False, "actual": actual}
```
This is the Verifier's job for this domain: checking commits, not checking whether the
Executor's narrative sounds plausible.

**New specialist models/roles.** Onboarded via the Domain Capability Matrix (03) - new
row, low confidence, zero evidence count. No separate onboarding mechanism.

---

## Network Topology

**Fact freshness windows**, by type:

| Fact type | Recheck window | Why |
|---|---|---|
| Device connectivity (e.g. ADB status) | Daily | Drops independent of IP stability - OS-level flakiness, not routing |
| IP/routing/reservation state (core fleet) | Every 3-6 days | Stable since reservations replaced DHCP; window should lengthen as stability holds |
| Guest-device IPs | Dynamic DHCP pool | Not dispatch-relevant; no fixed window |

**External-provider-imposed constraints.** Hard locks, distinct from an internal
decision like INFRA-005 - re-testing risks a real outage, so no casual "evidence
supersedes a lock" flow:
```
1. Constraint imposed by an external provider (e.g. ISP refuses DHCP to a downstream
   router, so the WAN side must stay static)
2. Treat as hard lock -- not open to casual re-test
3. Has the provider's policy actually changed?
   - Confirmed WITH THE PROVIDER, never guessed or inferred from a single reconnect
   - No  -> constraint stands, no re-test
   - Yes -> re-test carefully: off-peak window, rollback plan ready before attempting
```

---

## Web Apps / UI

Tasks where verification requires actually seeing a rendered page - layout, visual
state, interactive behavior - not just reading the code. Sixth domain.

**Routing.** Requires `tool_access: browser` (or `both`, paired with file/shell work on
the same item) per 03's Executor-subtype. Executor-Browser (browser-use + VNC) is
mandatory; Executor-Aider completing the code change is not sufficient alone.

**Verification artifact.** The VNC stream / screenshot capture from Executor-Browser is
the Verifier's evidence - not the diff, not a self-reported "looks right." Domain
instance of 01's Detection axis: a completion claim with no captured render artifact is
unverified (D stays high) until that artifact exists.

```python
def verify_web_render_claim(claim, capture_fn) -> dict:
    """Mirrors the commit-backed verification pattern above: a claim is not accepted
    on narrative alone. capture_fn must run a FRESH capture, never a cached one."""
    artifact = capture_fn()
    if artifact is None:
        return {"verified": False, "reason": "no_render_artifact_captured"}
    return {"verified": True, "artifact": artifact}
```

**Same gates, no new math.** Normal Risk Engine (01) and role routing (03) - this
section only locks which executor subtype is mandatory and what counts as evidence.
