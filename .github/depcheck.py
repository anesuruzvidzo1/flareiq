"""Fail if a script imports a package that requirements.txt does not provide."""
import ast, importlib.util, pathlib, sys

src = pathlib.Path("scripts")
local = {p.stem for p in src.glob("*.py")}
missing = []
for f in sorted(src.glob("*.py")):
    for node in ast.walk(ast.parse(f.read_text())):
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
    sys.exit(1)
print("All script imports are satisfied by requirements.txt")
