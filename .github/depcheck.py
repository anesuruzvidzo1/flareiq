"""Fail if a script imports a package that requirements.txt does not provide.

Imports inside a try block that catches ImportError are skipped: those are
optional by construction, and the code is expected to cope when they are absent.
"""
import ast
import importlib.util
import pathlib
import sys

OPTIONAL_ERRORS = {"ImportError", "ModuleNotFoundError"}


def _guarded_imports(tree: ast.AST) -> set[int]:
    """ids of import nodes sitting inside a try/except ImportError."""
    guarded: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Try):
            continue
        catches = False
        for handler in node.handlers:
            t = handler.type
            if isinstance(t, ast.Name) and t.id in OPTIONAL_ERRORS:
                catches = True
            elif isinstance(t, ast.Tuple) and any(
                isinstance(e, ast.Name) and e.id in OPTIONAL_ERRORS for e in t.elts
            ):
                catches = True
        if not catches:
            continue
        for stmt in node.body:
            for sub in ast.walk(stmt):
                if isinstance(sub, ast.Import | ast.ImportFrom):
                    guarded.add(id(sub))
    return guarded


def main() -> int:
    src = pathlib.Path("scripts")
    local = {p.stem for p in src.glob("*.py")}
    missing = []
    for f in sorted(src.glob("*.py")):
        tree = ast.parse(f.read_text())
        guarded = _guarded_imports(tree)
        for node in ast.walk(tree):
            if id(node) in guarded:
                continue
            if isinstance(node, ast.Import):
                mods = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                mods = [node.module.split(".")[0]]
            else:
                continue
            for m in mods:
                if m in local or m in sys.stdlib_module_names:
                    continue
                if importlib.util.find_spec(m) is None:
                    missing.append(f"{f.name}: {m}")
    if missing:
        print("Imports not satisfied by requirements.txt:")
        for x in sorted(set(missing)):
            print("  " + x)
        return 1
    print("All script imports are satisfied by requirements.txt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
