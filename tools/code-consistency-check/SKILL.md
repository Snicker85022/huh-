---
name: code-consistency-check
description: "Run a static rename-drift audit on a Python file BEFORE executing, testing, or importing it — and ALWAYS run it immediately after any 'let me rewrite this file cleanly' pass, any dataclass/function signature change, or any multi-step heredoc write. Catches the exact bug class that has repeatedly burned agent turns and hit recursion limits on this project — a function, dataclass field, or self.attribute gets renamed partway through writing/rewriting a file, and some call site still uses the old name, which Python only reports at runtime as a NameError/TypeError/AttributeError. Use this whenever you are about to run pytest, python -c, or start a service against a .py file you just wrote or edited; running the audit costs one command, and discovering the same bug via a traceback costs a full turn (or, at recursion-limit time, the whole task)."
---

# Code Consistency Check

## Why this exists

Across this project's agent sessions the same bug class has recurred at least five times, always in the same shape: a name (function, dataclass field, method parameter, `self.` attribute) gets renamed or restructured partway through writing/rewriting a file — usually during a "this is a mess, let me rewrite it cleanly" moment — and one or more call sites still reference the old name. Python does not catch this at write time. It surfaces later as a `NameError`, `TypeError: unexpected keyword argument`, or `TypeError: missing N required positional arguments`, discovered only when the file is actually run — sometimes several tool-calls later, after the actual cause has scrolled out of the working context. That gap between "wrote the bug" and "discovered the bug" burns agent turns and has twice hit the harness's recursion limit.

Concrete past incidents (all in this repo):
- `job_runner/scheduler/error_distill.py`: called `normalize_error(...)`, only `normalize_error_head(...)` was ever defined.
- `job_runner/scheduler/error_distill.py`: constructed `KnownFix(root_error=...)`, the dataclass field is `root_cause`.
- `job_runner/scheduler/error_distill.py`: constructed `DistillLesson(source=1)`, the dataclass field is `source_task_id`.
- tests: called `add_attempt(...)` with 7 positional args; the function requires 8 (missing `prompt`, silently shifting every arg after it).
- tests: called `detect_collapse(..., window=3)`; the parameter is `n_samples`.
- `pm_web/service.py`: defined `page(title, active, body)`, both route handlers called `shell(title, body)` — a name AND arity mismatch left over from an earlier draft.

None of these were logic bugs. Every one was a rename that didn't propagate. This skill exists to catch that class mechanically, in about a second, instead of via a runtime traceback.

When to run it:

Run `scripts/audit_refs.py` on a file:
1. Immediately after writing or rewriting it (heredoc, create_file, str_replace spanning a def/class) — before the first `python -c`, `pytest`, or service start against it.
2. Whenever you say (to yourself) some version of "let me rewrite this cleanly" / "this is a mess" / "let me redo this file" — that is the exact moment past incidents happened. Run the audit on the new version before testing it.
3. After any signature change — renaming a function, a dataclass field, a `self.` attribute, or a parameter name — re-audit every file that might call it, not just the file you edited.
4. Before declaring a module "written" or moving on to the next file in a multi-file build — audit each one as you finish it, not in a batch at the end.

This is a pre-flight check, not a replacement for actually running the tests. Both matter: the audit catches rename drift in ~1 second; the test run catches everything else.

How to run it:

```bash
python3 <skill_dir>/scripts/audit_refs.py path/to/file.py [path/to/other_file.py ...]
```

Exit code `0` = no findings (still run your tests as normal). Exit code `1` = findings printed, one per line, with the line number and what's wrong. Fix every finding before running the file.

What it catches (and what it deliberately doesn't):

Catches within a single file:
- Calls to a name with no matching `def` / `class` / import anywhere in the file (`undefined-call`).
- Calls to a locally-defined function or `@dataclass` with a keyword argument that isn't a real parameter/field name (`bad-keyword`).
- Calls with too many positional arguments for the target's signature (`too-many-positional`).
- Calls missing a required positional-or-keyword argument (`missing-required`) — catches silent arg-shift bugs, where a missing argument doesn't error on count but silently reassigns every argument after it.
- `self.x` read inside a class where `self.x` is never assigned anywhere in that class (`self-attr-missing`) — catches typo'd instance attributes.

Deliberately does NOT try to resolve (false negatives here are fine — false positives are not, and would train you to ignore the tool):
- Cross-file calls — audit both files; each is checked independently.
- Calls through `**kwargs`-spread, `*args`-spread, or dynamic dispatch (`getattr`, decorators that alter signatures).
- Method calls on non-`self` objects (only `self.method(...)` inside the defining class is checked).
- Anything requiring actual type inference — this is a name/arity checker, not a type checker.

A clean run (`0 findings`) does not mean the file is correct — it means this specific bug class was not found. Still run the real tests.

If it finds something:

Fix the call site (or the definition, whichever is actually correct against current intent) directly — don't guess; open the definition and match it exactly. Re-run the audit on the same file until it's clean, then proceed to running the actual tests. Make the fix, rerun, move on.
