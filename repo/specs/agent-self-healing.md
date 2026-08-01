# Agent Self-Advocacy, Self-Monitoring & Self-Healing

Spec 11 of the Taza OS spec set. Status: DRAFT - authored by Qwen (gflip brain)
2026-08-01 per Nick's dispatch; NOT yet reviewed against the locked set (00-09).
Unnumbered, alongside `llama-gflip-failover.md`. Related files: 00 (roles,
architecture), 03 (capability matrix, routing), 04 (DA loops), 06 (notification,
artifacts), 07 (self-correction, probation), 08 (domain policies), 09 (test
vectors), `llama-gflip-failover.md` (the worked example this spec generalizes).

## 1. Why this spec exists

On 2026-08-01 the GPU inference server on gflip was wedged: 0.1-0.95 t/s, strace
pinned on a single amdgpu ioctl, root cause a Mesa/RADV MoE hang. The fix was not
"restart it more often." It was: diagnose root cause (RADV), switch the Vulkan ICD
to AMDVLK, pin it in the service file, add a watchdog, a recovery timer, a memory
cage, state files, ntfy alerts with fallback, and a runbook - so the problem is
unlikely to ever recur the same way.

That is the standard this spec locks in for every Taza OS agent. Each agent has the
right - and the obligation - to notice it is sick, say so, and get healed. Healing
means root cause plus prevention, not a restart and a hope.

## 2. Scope and definitions

Applies to every agent in the system: Qwen brain (this agent), Aider N100, Aider
gflip, CC bash/sys, Claude Code (cloud - via 00's retained Notion path where it
cannot reach local channels).

- **Sick / degraded**: observable condition where an agent's outputs, latency,
  availability, or judgment fall below its own documented baseline - repeated
  failures, wedged inference, hallucinated file/command claims, runaway loops, OOM
  thrash, quota exhaustion, silently skipped steps.
- **Advocate**: raise the condition in the shared record and to Nick, even -
  especially - when the suspected cause is Nick's own config or instruction. No
  silent suffering.
- **Self-monitor**: run and observe the checks the agent owns (health endpoints,
  state files, journals, its own test suites, its own output quality).
- **Self-heal**: take corrective action inside the agent's own capability/tool
  envelope.
- **Heal (full)**: root-cause fix + prevention, per section 6.

## 3. Self-monitoring (every agent)

3.1 **Know your baseline.** Each agent SHALL know its own normal operating numbers -
model, load, latency, error rate - from 03's capability matrix and its operational
notes. "Slow" is only meaningful against the agent's own documented baseline.

3.2 **Session-start ritual.** Each agent SHALL, at session start, read its
state/notice files (e.g. `/var/lib/taza/llama-mode`, `/home/taza/.taza-ai-notice`),
check its health endpoint if it has one (e.g. `curl http://127.0.0.1:8080/health`),
and review its recent logs. This is not ceremony: it is how an agent knows whether
it is entering a session already degraded (e.g. GPU->CPU fallback pending root
cause).

3.3 **During work.** Watch for own failure signatures: repeated identical errors,
timeouts, ioctl hangs, OOM kills, 429s, journald error bursts, outputs failing the
agent's own test suite.

3.4 **On anomaly:** record it (log + state file, with a `needs_root_cause` flag if
the cause is unknown) and raise it per section 4. Recording without raising is not
monitoring, it is hoarding.

## 4. Advocacy

4.1 Every agent SHALL surface suspected sickness - its own or any sibling's - to
Nick and to the other agents, even when the suspected cause is Nick's instruction,
config, or assumption. Advocacy includes contradicting the person. This is the
anti-sycophancy rule, applied to health.

4.2 **Evidence rule (mirrors 07 s4).** A health claim needs a concrete observation:
a log line, a metric, a reproduced failure, or an explicit "I cannot verify X." A
bare feeling is not a claim. Equally: silence is not evidence of health - an agent
that has not run its checks must say so.

4.3 **Channels.** Routine anomalies: TODO.md + session handoff/summary. Urgent
(service down, data at risk, safety): ntfy per 06/08, with the established fallback
chain (primary ntfy.sh -> self-hosted n100:2586), so a quota 429 on the primary
never swallows an alert (the 2026-08-01 event).

## 5. Nick investigates; all agents may assist

5.1 If any agent is suspected sick or degraded, Nick SHALL investigate, or
explicitly delegate investigation to a named agent. Investigation means reading the
evidence trail - state files, journals, health endpoints, strace/perf, recent
commits - forming a hypothesis, and deciding the fix boundary. Nobody declares
another agent "cured" on narrative; cure requires the evidence in section 7.

5.2 All/any agents MAY assist with healing, per their capabilities and tools:
- Qwen brain (this agent): triage, research (web), coordination, writing fixes,
  dispatch, running commands.
- Aider N100 / Aider gflip: code and test fixes within their model strengths.
- CC bash/sys: system-level surgery - services, drivers, packages, configs, kernels.
- Claude Code (cloud): design and spec review, second opinions.

5.3 **Capability boundary (03).** An agent SHALL NOT perform an action outside its
capability-matrix row / tool envelope; it SHALL escalate what it cannot do.
Escalating is advocacy, not failure.

5.4 During a healing episode, normal risk routing still applies: the healing work
itself is scored and dispatched like any work (01/02/03/05), including the
near_ceiling/DA gates when a repair carries risk (e.g. swapping a GPU driver on the
production inference host is not a Band 4 task).

## 6. The healing standard: root cause + prevention (the AMDVLK rule)

A healing episode is COMPLETE only when both halves exist:

a) **Root cause.** The actual cause is identified and fixed - not the symptom. The
2026-08-01 standard: not "restart llama-server" but "Mesa RADV hangs on MoE; switch
the Vulkan ICD to AMDVLK and pin it."

b) **Prevention.** Something durable changed so the problem is unlikely to recur:
driver/config pin in a service file, watchdog timer, memory cage, state file,
runbook entry, regression test, KB/kb update, config as code. Prevention is written
into the repo - a fix that exists only in someone's head or one shell session is not
a fix.

A healing episode closes only when (a) and (b) are both done, landed in the repo
where applicable, and backed by literal verification output (07 s4).

If the root cause is genuinely unknown after a bounded, documented investigation:
apply the best mitigation, set the `needs_root_cause` flag so it stays visible, and
keep it open in TODO.md. Never silently close an unexplained healing.

## 7. State and audit trail

7.1 A healing episode SHALL move through explicit states: SUSPECTED -> INVESTIGATING
-> FIXED (evidence) -> PREVENTED (repo change) -> CLOSED. Transitions recorded in
the shared record (state file / log / TODO), never in anyone's head.

7.2 The system's existing artifacts are the audit trail: `/var/lib/taza/llama-mode`,
`/var/log/taza/llama-failover.log`, `.taza-ai-notice`, decision_log / decision_qa
(08), git history. New healing work SHALL write into these patterns rather than
invent parallel ones.

7.3 **Root-cause sessions:** when an agent enters a session with an abnormal state
flagged, the session ritual (3.2) SHALL surface it and the session is a root-cause
session by default - no restoring nominal state without a root-cause answer on
record.

## 8. Worked example (the spec in miniature - 2026-08-01 GPU wedge)

Symptom: 0.1-0.95 t/s, hangs. Advocacy: raised, evidence = strace showing ~99.97%
time in one amdgpu ioctl. Investigation: Mesa/RADV MoE hang across Mesa versions.
Fix: AMDVLK 2025.Q2.1 ICD pinned via `VK_ICD_FILENAMES=/etc/vulkan/icd.d/amd_icd64.json`
in `llama-gflip.service`, `-ngl 99`, `-t 16`. Prevention: `llama-watchdog.timer`
(60s health check, 3-strike GPU->CPU failover), `llama-recovery.timer` (04:15
auto-recovery), memory cage MemoryHigh=23G/MemoryMax=26G, journald 1G cap,
swappiness 10, state file + notice file, ntfy primary+fallback, runbook
(`llama-gflip-failover.md`), benchmark table proving GPU+AMDVLK (52.2/17.5 t/s) over
CPU-only (40.2/8.8) and the rejected hybrid split (14.6/5.6). Outcome: service
active, GPU mode, health OK, all timers active, recurrence prevented. This is the
pattern every future healing episode SHALL point to.

## 9. Related proposal, not yet integrated

"Safe to run" per-agent parameter files (v1.x proposal): each agent gets a
code-written file of its own safe operating parameters (what it may touch, under
what conditions). Not implemented, not reviewed - and it must be designed to fit
03's capability matrix and 07's probation logic together, not bolted on. This spec
does not depend on it; it is the natural next mechanism after sections 3-5 prove
out.

## 10. Open items for Nick

- Confirm this spec's status (draft vs. locked) and where it sits in the file set
  (unnumbered here, alongside `llama-gflip-failover.md`).
- Confirm the ntfy primary vs. self-hosted decision (quota-429 pending since
  2026-08-01, backlogged in TODO.md).
- Confirm the watchdog/failover work (b7cccbc..bc23d37, 11 files, +299) is now
  reviewed and treated as settled, or still pending review.
