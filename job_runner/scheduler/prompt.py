"""Goal 1 -- Prompt Reconstruction / Engineering.

Assembles Ornith's system + user prompt from structured pieces (role, task
scope, constraints, tools, workspace, output contract, negative examples)
instead of one hand-written block. Pure string composition, CPU, runs once per
attempt. Deliberately boring (1970s mail-merge): the discipline comes from
every task going through the same template, not from cleverness.

Reproducibility contract (spec Goal 1 test criterion c): same inputs MUST
produce byte-identical output, so this module embeds no timestamps, no random
values, no absolute ordering beyond the input order.
"""
from __future__ import annotations

from typing import Iterable, Mapping, Optional

SYSTEM_PROMPT = (
    "You are Ornith, a senior staff engineer working autonomously on exactly "
    "one scoped task inside an isolated workspace on a local machine. "
    "You write complete, correct, self-contained code. You follow the "
    "constraints below exactly. You do not ask questions; you deliver a "
    "solution. You do not repeat approaches that are labeled as known "
    "failures."
)

_TEMPLATE = """## Task
Title: {title}

{description}

## Constraints (each one applies verbatim; do not relax any)
{constraints_bullets}

## Tools available
Only the tools listed here exist in this environment. Do not invent, import,
or reference tools outside this list. If the list is empty, you may use the
standard library and the shell provided by the verifier only.
{tools_bullets}

## Workspace
All work happens in: {workspace}
Write your complete solution to: {target_file}
The solution is evaluated by an automated acceptance command and must be
complete, self-contained, and syntactically valid as written.

## Output contract
Emit exactly ONE fenced code block ({lang_hint}) containing the complete
contents of {target_file}. No prose around it, no explanations inside the
block, no duplicate blocks. The block must be the final answer.

## Known-failure context (if any)
{negative_examples}
"""


def _bullets(items: Iterable[str]) -> str:
    items = [i.strip() for i in items if i and i.strip()]
    if not items:
        return "  (none)"
    return "\n".join(f"  - {i}" for i in items)


def assemble_prompt(
    title: str,
    description: str,
    constraints: Iterable[str],
    tools: Iterable[str],
    workspace: str,
    target_file: str,
    negative_examples: str = "",
    lang_hint: str = "python",
) -> str:
    """Assemble the user prompt for one attempt. Deterministic in all inputs."""
    user = _TEMPLATE.format(
        title=title,
        description=(description or "(no description provided)").strip(),
        constraints_bullets=_bullets(constraints),
        tools_bullets=_bullets(tools),
        workspace=workspace,
        target_file=target_file,
        lang_hint=lang_hint,
        negative_examples=(negative_examples or "  (none yet)").strip(),
    )
    return user
