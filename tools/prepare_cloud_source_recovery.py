"""Prepare source-only Molab bootstrap; never packages data or credentials.

Local execution only prepares the transport payload. Compilation and experiments
remain remote. Existing differing remote files are refused, never overwritten.
"""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOWED = {".py", ".rs", ".cpp", ".cu", ".cuh", ".h", ".hpp", ".inc", ".toml", ".md"}


def main():
    paths = []
    for folder in ("native", "src", "reference", "tools", "configs", "docs"):
        paths.extend(p for p in (ROOT / folder).rglob("*") if p.is_file() and p.suffix in ALLOWED)
    paths.extend(ROOT / name for name in ("Cargo.toml", "build.rs", "WORK_PLAN.md", "NATIVE_ARCHITECTURE.md", "README.md"))
    # These are source generation / experiment recipes, not their outputs.
    paths.extend((ROOT / "build").glob("molab_*.py"))
    sources = {}
    for path in sorted(set(paths)):
        rel = path.relative_to(ROOT).as_posix()
        if any(part in {"__pycache__", ".venv"} for part in path.parts):
            continue
        content = path.read_text(encoding="utf-8-sig")
        # Never transfer local pairing credentials or a credential-bearing URL.
        if re.search(r"(?:Bearer |sb[.]molab[.]run/session/)ey[A-Za-z0-9_-]{20,}", content):
            raise ValueError("Credential-like source rejected: " + rel)
        sources[rel] = content
    manifest = {name: hashlib.sha256(content.encode()).hexdigest() for name, content in sources.items()}
    bootstrap = '''"""Source-only recovery bootstrap. Does not run experiments or claim results."""
from pathlib import Path
import hashlib
SOURCES = ''' + repr(sources) + '''
def restore(root="/marimo/fly-project"):
    root = Path(root)
    for name, text in SOURCES.items():
        path = root / name
        if path.exists() and path.read_text(encoding="utf-8-sig") != text:
            raise RuntimeError("Refusing differing existing source: " + name)
    for name, text in SOURCES.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text(text, encoding="utf-8")
        assert path.read_text(encoding="utf-8-sig") == text
    return {"verified_source_files": len(SOURCES), "results_restored": False}
'''
    # Restore into a separate recovery root so older cloud sources stay intact.
    payload = "from pathlib import Path\nimport runpy,json\n"
    payload += "p=Path('/marimo/fly_source_recovery.py')\n"
    payload += "p.write_text(" + repr(bootstrap) + ",encoding='utf-8')\n"
    payload += "m=runpy.run_path(str(p));print(json.dumps(m['restore']('/marimo/fly-recovered-sources')))\n"
    output = ROOT / "build/cloud_source_recovery_payload.py"
    output.write_text(payload, encoding="utf-8")
    (ROOT / "build/cloud_source_recovery_manifest.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps({"source_files": len(sources), "payload_bytes": output.stat().st_size}))


if __name__ == "__main__":
    main()
