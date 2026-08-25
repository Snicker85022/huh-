#!/usr/bin/env python3
"""Tests for circuit_breaker.py -- run with: python3 test_circuit_breaker.py

Also pytest-compatible (functions named test_*).
"""

import ast
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerError,
    STATUS_ACTIVE,
    STATUS_FROZEN,
    STATUS_HARD_STOP,
    COMPROMISED_JUDGMENT,
    REASON_CODE_HASH,
    REASON_ERROR_SIG,
    normalize_ast_hash,
    normalize_error_signature,
)

# Same semantic code ("def add(a, b): return a + b"), three different formats.
FIX_FORMATS = [
    "def add(a, b):\n    return a + b\n",
    "def add(a,b):\n\treturn a+b\n",          # tabs / no spaces
    "def add(a, b): return a + b\n",           # single line
]


def test_reformatting_produces_same_ast_hash():
    h1, h2, h3 = (normalize_ast_hash(c) for c in FIX_FORMATS)
    assert h1 == h2 == h3, "reformatting must not change the code hash"


def test_semantically_different_code_produces_different_hash():
    good = normalize_ast_hash("def add(a, b):\n    return a + b\n")
    bad = normalize_ast_hash("def add(a, b):\n    return a - b\n")
    assert good != bad, "semantic change must change the code hash"


def test_syntax_error_fallback_normalizes_formatting():
    broken_1 = "def broken(:\n    return\n"
    broken_2 = "def broken(: return"
    broken_3 = "def broken(:\n return\n"
    assert normalize_ast_hash(broken_1) == normalize_ast_hash(broken_2)
    assert normalize_ast_hash(broken_1) == normalize_ast_hash(broken_3)
    assert normalize_ast_hash(broken_1) != normalize_ast_hash("def other(:\n")


def test_three_identical_code_hashes_freeze_compromised():
    cb = CircuitBreaker("task-fix")
    errs = ["TypeError: boom A", "TypeError: boom B", "TypeError: boom C"]
    o1 = cb.record_attempt(FIX_FORMATS[0], errs[0])
    o2 = cb.record_attempt(FIX_FORMATS[1], errs[1])
    assert o1.status == STATUS_ACTIVE and o1.accepted
    assert o2.status == STATUS_ACTIVE and o2.accepted
    assert cb.status == STATUS_ACTIVE  # 2 identical hashes is NOT a freeze

    o3 = cb.record_attempt(FIX_FORMATS[2], errs[2])
    assert o3.freeze_reason == REASON_CODE_HASH
    assert cb.status == STATUS_FROZEN
    assert cb.judgment == COMPROMISED_JUDGMENT
    assert cb.freeze_cycles == 1


def test_two_consecutive_identical_error_signatures_freeze():
    cb = CircuitBreaker("task-err")
    o1 = cb.record_attempt(
        "def f(x): return x",
        "TypeError: 'NoneType' object is not subscriptable at line 12",
    )
    assert o1.status == STATUS_ACTIVE

    o2 = cb.record_attempt(
        "def g(x): return x",  # different code, same failure
        "TypeError: 'NoneType' object is not subscriptable at line 48",
    )
    assert o2.freeze_reason == REASON_ERROR_SIG
    assert cb.status == STATUS_FROZEN


def test_error_signature_ignores_line_numbers_but_not_type():
    sig_a = normalize_error_signature(
        "TypeError: 'NoneType' object is not subscriptable at line 12"
    )
    sig_b = normalize_error_signature(
        "TypeError: 'NoneType' object is not subscriptable at line 48"
    )
    sig_c = normalize_error_signature("KeyError: 'foo' at line 12")
    assert sig_a == sig_b
    assert sig_a != sig_c


def test_non_consecutive_identical_errors_do_not_freeze():
    cb = CircuitBreaker("task-nc")
    sig = "ValueError: bad value at line 3"
    cb.record_attempt("def a(): pass", sig)
    cb.record_attempt("def b(): pass", "ValueError: other thing at line 9")
    o3 = cb.record_attempt("def c(): pass", sig)
    assert o3.accepted
    assert cb.status == STATUS_ACTIVE
    assert cb.freeze_cycles == 0


def test_passing_attempt_never_counts_toward_error_freeze():
    cb = CircuitBreaker("task-pass")
    o1 = cb.record_attempt("def f(): return 1", None)
    o2 = cb.record_attempt("def g(): return 2", None)
    assert o1.accepted and o2.accepted
    assert cb.status == STATUS_ACTIVE


def test_two_freeze_cycles_hard_stop_and_no_retries():
    cb = CircuitBreaker("task-hard")

    # Cycle 1: 3 identical (modulo formatting) broken fixes -> frozen.
    o = cb.record_attempt(FIX_FORMATS[0], "error one")
    o = cb.record_attempt(FIX_FORMATS[1], "error two")
    o = cb.record_attempt(FIX_FORMATS[2], "error three")
    assert o.freeze_reason == REASON_CODE_HASH
    assert cb.status == STATUS_FROZEN
    assert cb.freeze_cycles == 1

    # Cycle 2: counters reset; 3 more identical broken fixes -> hard stop.
    o = cb.record_attempt(FIX_FORMATS[0], "error four")
    o = cb.record_attempt(FIX_FORMATS[1], "error five")
    o = cb.record_attempt(FIX_FORMATS[2], "error six")
    assert o.hard_stop
    assert cb.status == STATUS_HARD_STOP
    assert "needs human review" in cb.status
    assert cb.freeze_cycles == 2

    # No further retries accepted.
    o = cb.record_attempt("def fresh(): pass", None)
    assert o.accepted is False and o.hard_stop

    try:
        cb.retry_context("base")
        raise AssertionError("retry_context must raise after hard stop")
    except CircuitBreakerError:
        pass


def test_retry_context_includes_labeled_negative_examples():
    cb = CircuitBreaker("task-ctx")
    cb.record_attempt(
        "def broken_one(): return x +",
        "SyntaxError: bad at line 1",
    )
    o = cb.record_attempt(
        "def broken_two(): return x +",
        "SyntaxError: bad at line 1",
    )
    assert o.freeze_reason == REASON_ERROR_SIG
    assert cb.status == STATUS_FROZEN

    ctx = cb.retry_context("ORIGINAL INSTRUCTION")
    assert "ORIGINAL INSTRUCTION" in ctx
    assert ctx.count("--- NEGATIVE EXAMPLE #") == 2
    assert "do not reuse" in ctx.lower()
    assert "broken_one" in ctx and "broken_two" in ctx
    assert "SyntaxError" in ctx


def test_hardware_contract_cpu_only_stdlib_imports():
    here = os.path.dirname(os.path.abspath(__file__))
    src = open(os.path.join(here, "circuit_breaker.py"), encoding="utf-8").read()
    tree = ast.parse(src)
    allowed = {"__future__", "ast", "hashlib", "re", "time", "dataclasses", "typing"}
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
    extra = imports - allowed
    assert not extra, (
        "circuit_breaker.py imports non-CPU-guardrail modules: "
        f"{sorted(extra)}"
    )


def _run_all():
    tests = [
        obj for name, obj in sorted(globals().items())
        if name.startswith("test_") and callable(obj)
    ]
    failed = []
    for t in tests:
        try:
            t()
        except AssertionError as e:
            failed.append((t.__name__, f"AssertionError: {e}"))
        except Exception as e:  # noqa: BLE001
            failed.append((t.__name__, f"{type(e).__name__}: {e}"))
        else:
            print(f"PASS  {t.__name__}")
    for name, msg in failed:
        print(f"FAIL  {name}: {msg}")
    print(f"\n{len(tests) - len(failed)}/{len(tests)} tests passed.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(_run_all())
