# Repo — Primary Work Hub Handoff

**Role:** Core workspace repository (DOE reports, validation tools, job runner).  
**Git Branch:** `master`  
**Identity & Operating Guidelines:** See `CLAUDE.md`.  
**Detailed History:** See `SESSION_HANDOFF_2026-08-03.md`.

---

## Tooling & Gates

- **Code Consistency Audit Gate:**
  ```bash
  /home/taza/repo/job_runner/.venv/bin/python /home/taza/repo/tools/code-consistency-check/scripts/audit_refs.py <path_to_file.py>
  ```
  *Mandatory check before running any `.py` script.*

- **Job Runner & Scheduler:**
  - Located in `job_runner/`
  - Circuit breaker test suite: `job_runner/tests/test_circuit_breaker.py`
