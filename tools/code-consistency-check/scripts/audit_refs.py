#!/usr/bin/env python3
"""audit_refs.py -- catch rename-drift bugs BEFORE executing a Python file.

Rename drift = a function/dataclass field/self.attr is renamed partway through a
file, and a call site still uses the old name. Python reports it only at runtime
(NameError/TypeError/AttributeError). This is a pure-stdlib, single-file AST
checker that flags, WITHIN A FILE ONLY:

  1. Calls to a name with no def/class/import/param in the same file -> undefined-call
  2. Calls to a local function/@dataclass with a keyword that isn't
     one of its declared params / dataclass fields                  -> bad-keyword
  3. Calls with more positionals than the signature allows          -> too-many-positional
  4. Calls missing a required parameter                             -> missing-required
  5. Reads of self.x in a class where self.x is never assigned and
     is not a dataclass field, method, or common constant           -> self-typo

It deliberately does NOT resolve cross-file calls, imports, kwargs/args spread,
dynamic dispatch (getattr, decorators that alter signatures), or attribute
chains beyond the current class. False negatives are fine; false POSITIVES are
not. A clean run does NOT mean the code is correct -- run the real tests too.

Usage:
    python3 audit_refs.py path/to/file.py [path/to/other.py ...]
Exit 0 = no findings. Exit 1 = findings, one per line.
"""
from __future__ import annotations

import ast
import sys
from dataclasses import dataclass
from typing import Dict, List, Optional, Set


@dataclass
class Finding:
    line: int
    kind: str
    message: str


@dataclass
class CallableSig:
    name: str
    kind: str                  # "function" | "dataclass"
    param_names: List[str]
    required: Set[str]         # positional-or-keyword params with no default
    has_varargs: bool
    has_varkw: bool
    max_pos: Optional[int]      # None when *args present


# ---------------------------------------------------------------------------
# signature collection
# ---------------------------------------------------------------------------
def _dataclass_sig(cls: ast.ClassDef) -> Optional[CallableSig]:
    decorated = any(
        (isinstance(d, ast.Name) and d.id == "dataclass")
        or (isinstance(d, ast.Call) and isinstance(d.func, ast.Name) and d.func.id == "dataclass")
        for d in cls.decorator_list
    )
    if not decorated:
        return None
    names: List[str] = []
    required: Set[str] = set()
    for stmt in cls.body:
        if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
            names.append(stmt.target.id)
            if stmt.value is None:
                required.add(stmt.target.id)
    return CallableSig(
        name=cls.name, kind="dataclass", param_names=names, required=required,
        has_varargs=True, has_varkw=False, max_pos=None,
    )


def _func_sig(fn: ast.FunctionDef, skip_self: bool) -> CallableSig:
    a = fn.args
    posonly = [p.arg for p in a.posonlyargs]
    pos = [p.arg for p in a.args]
    all_pos = posonly + pos
    if skip_self and all_pos and all_pos[0] in ("self", "cls"):
        all_pos = all_pos[1:]
    n_defaults = len(a.defaults)
    required_pos = all_pos[: len(all_pos) - n_defaults] if n_defaults else all_pos
    kwonly = [k.arg for k in a.kwonlyargs]
    kwonly_required = {k.arg for k, d in zip(a.kwonlyargs, a.kw_defaults) if d is None}
    param_names = all_pos + kwonly
    required = set(required_pos) | kwonly_required
    return CallableSig(
        name=fn.name, kind="function", param_names=param_names, required=required,
        has_varargs=a.vararg is not None, has_varkw=a.kwarg is not None,
        max_pos=None if a.vararg else len(all_pos),
    )


def collect_signatures(tree: ast.Module):
    sigs: Dict[str, CallableSig] = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            sigs[node.name] = _func_sig(node, skip_self=False)
        elif isinstance(node, ast.ClassDef):
            dc = _dataclass_sig(node)
            if dc is not None:
                sigs[node.name] = dc
            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    sigs[f"{node.name}.{sub.name}"] = _func_sig(sub, skip_self=True)
    return sigs


def imported_names(tree: ast.Module) -> Set[str]:
    names: Set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                names.add((a.asname or a.name).split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            for a in node.names:
                names.add(a.asname or a.name)
    return names


def all_local_params(tree: ast.Module) -> Set[str]:
    names: Set[str] = set()
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            a = n.args
            for p in list(a.posonlyargs) + list(a.args) + list(a.kwonlyargs):
                names.add(p.arg)
            if a.vararg:
                names.add(a.vararg.arg)
            if a.kwarg:
                names.add(a.kwarg.arg)
    return names


def any_def_named(tree: ast.Module, name: str) -> bool:
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n.name == name:
            return True
        if isinstance(n, (ast.Assign, ast.AnnAssign)):
            t = getattr(n, "target", None)
            if isinstance(t, ast.Name) and t.id == name:
                return True
    return False


# ---------------------------------------------------------------------------
# call checks
# ---------------------------------------------------------------------------
def _check_args(node: ast.Call, sig: CallableSig, findings: List[Finding]) -> None:
    if not sig.has_varkw:
        for kw in node.keywords:
            if kw.arg is None:
                continue
            if kw.arg not in sig.param_names:
                findings.append(Finding(
                    node.lineno, "bad-keyword",
                    f"`{sig.name}(...)` called with keyword `{kw.arg}=` -- not a real "
                    f"parameter/field of {sig.kind} `{sig.name}` "
                    f"(known: {', '.join(sig.param_names) or '(none)'})",
                ))
    if any(isinstance(a, ast.Starred) for a in node.args):
        return
    n_pos = len(node.args)
    if sig.max_pos is not None and n_pos > sig.max_pos:
        findings.append(Finding(
            node.lineno, "too-many-positional",
            f"`{sig.name}(...)` called with {n_pos} positional args, "
            f"but only takes {sig.max_pos}",
        ))
    kw_names = {kw.arg for kw in node.keywords if kw.arg}
    pos_names = sig.param_names[:n_pos]
    missing = {r for r in sig.required if r not in pos_names and r not in kw_names}
    if missing and not sig.has_varkw:
        findings.append(Finding(
            node.lineno, "missing-required",
            f"`{sig.name}(...)` called with {n_pos} positional + {len(kw_names)} keyword "
            f"args -- missing required: {', '.join(sorted(missing))}",
        ))


def check_calls(tree, sigs, imports, local_params) -> List[Finding]:
    findings: List[Finding] = []
    builtins_ok = set(dir(__builtins__)) if not isinstance(__builtins__, dict) else set(__builtins__.keys())
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name):
            name = func.id
            if name in sigs:
                _check_args(node, sigs[name], findings)
            elif (name not in imports and name not in builtins_ok
                  and name not in local_params and name not in ("self", "cls")
                  and not name.startswith("_")):
                if not any_def_named(tree, name):
                    findings.append(Finding(
                        node.lineno, "undefined-call",
                        f"call to `{name}(...)` -- no def/class/import for `{name}` "
                        f"found in this file",
                    ))
        elif isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name) \
                and func.value.id == "self":
            candidates = [v for k, v in sigs.items() if k.endswith(f".{func.attr}")]
            if len(candidates) == 1:
                _check_args(node, candidates[0], findings)
    return findings


# ---------------------------------------------------------------------------
# self.attr checks (lenient: avoids dataclass-field & bound-method false positives)
# ---------------------------------------------------------------------------
def check_self_attrs(tree: ast.Module) -> List[Finding]:
    findings: List[Finding] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        assigned: Set[str] = set()
        method_names = {
            sub.name for sub in node.body
            if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        for stmt in node.body:
            if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                assigned.add(stmt.target.id)
            if isinstance(stmt, ast.Assign):
                targets = stmt.targets if isinstance(stmt.targets, list) else [stmt.targets]
                for t in targets:
                    if isinstance(t, ast.Name):
                        assigned.add(t.id)
        reads: List[tuple] = []
        for sub in ast.walk(node):
            if isinstance(sub, ast.Attribute) and isinstance(sub.value, ast.Name) \
                    and sub.value.id == "self":
                if isinstance(sub.ctx, ast.Store):
                    assigned.add(sub.attr)
                elif isinstance(sub.ctx, ast.Load):
                    reads.append((sub.attr, sub.lineno))
        common = {"__class__", "__dict__"}
        for attr, lineno in reads:
            if attr in common:
                continue
            if attr in method_names:
                continue  # self._method / bound method read
            if attr not in assigned:
                findings.append(Finding(
                    lineno, "self-attr-missing",
                    f"class `{node.name}`: reads `self.{attr}` but never assigns it "
                    f"anywhere in the class (possible typo of another self.attr)",
                ))
    return findings


# ---------------------------------------------------------------------------
def audit_file(path: str) -> List[Finding]:
    src = open(path, encoding="utf-8").read()
    tree = ast.parse(src, filename=path)
    sigs = collect_signatures(tree)
    imports = imported_names(tree)
    local_params = all_local_params(tree)
    findings = check_calls(tree, sigs, imports, local_params)
    findings += check_self_attrs(tree)
    findings.sort(key=lambda f: f.line)
    return findings


def main(argv: List[str]) -> int:
    if not argv:
        print("usage: audit_refs.py file.py [file.py ...]", file=sys.stderr)
        return 2
    any_findings = False
    for path in argv:
        try:
            findings = audit_file(path)
        except SyntaxError as e:
            print(f"{path}: SYNTAX ERROR at line {e.lineno}: {e.msg}")
            any_findings = True
            continue
        if not findings:
            print(f"{path}: clean (0 findings)")
            continue
        any_findings = True
        print(f"{path}: {len(findings)} finding(s)")
        for f in findings:
            print(f"  line {f.line}: [{f.kind}] {f.message}")
    return 1 if any_findings else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
