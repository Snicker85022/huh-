"""Goal 1 tests: reproducibility, verbatim constraints, tool filtering."""
import pytest

from scheduler.prompt import assemble_prompt


def sample(**kw):
    base = dict(
        title="Implement nth_prime",
        description="Return the n-th prime number (1-indexed).",
        constraints=["Use only the standard library", "No global variables",
                     "Function must be named nth_prime"],
        tools=["run_python", "read_file"],
        workspace="/tmp/ws-x",
        target_file="solution.py",
    )
    base.update(kw)
    return base


def test_reproducible_byte_identical():
    a = assemble_prompt(**sample())
    b = assemble_prompt(**sample())
    assert a == b
    assert a.encode("utf-8") == b.encode("utf-8")


def test_constraints_verbatim():
    p = assemble_prompt(**sample())
    for c in sample()["constraints"]:
        assert c in p


def test_only_relevant_tools_listed():
    p = assemble_prompt(**sample())
    assert "run_python" in p and "read_file" in p
    assert "write_file" not in p
    assert "screenshot" not in p


def test_no_tools_means_none_listed():
    p = assemble_prompt(**sample(tools=[]))
    assert "(none)" in p
    assert "run_python" not in p


def test_target_file_and_workspace_interpolated():
    p = assemble_prompt(**sample(workspace="/srv/task-abc", target_file="main.py"))
    assert "/srv/task-abc" in p
    assert "main.py" in p


def test_negative_examples_injected_when_provided():
    p = assemble_prompt(**sample(negative_examples="NEGATIVE EXAMPLE #1\ncode x\nerror y"))
    assert "NEGATIVE EXAMPLE #1" in p
    assert "error y" in p


def test_negative_examples_placeholder_when_empty():
    p = assemble_prompt(**sample(negative_examples=""))
    assert "(none yet)" in p
