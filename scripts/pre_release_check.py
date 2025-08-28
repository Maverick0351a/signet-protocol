#!/usr/bin/env python
"""Pre-release validation script.

Checks:
- Tag format
- For core API tags (vX.Y.Z): versioned OpenAPI spec exists
- Changelog has matching section header
- For adapter tags (signet-langchain-vX.Y.Z): pyproject version aligns
"""
from __future__ import annotations
import argparse
import re
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]

CORE_TAG_RE = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")
LC_TAG_RE = re.compile(r"^signet-langchain-v(\d+)\.(\d+)\.(\d+)$")

def die(msg: str):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)

def check_changelog(tag: str):
    cl = ROOT / "CHANGELOG.md"
    if not cl.exists():
        die("CHANGELOG.md missing")
    content = cl.read_text(encoding="utf-8")
    if f"[{tag}]" not in content:
        die(f"CHANGELOG.md missing section for [{tag}]")
    print(f"✓ CHANGELOG contains section for {tag}")

def check_core_tag(tag: str, m: re.Match):
    version = m.group(0)[1:]  # strip leading v
    spec_path = ROOT / f"docs/api/openapi-{version}.yaml"
    if not spec_path.exists():
        die(f"Versioned spec {spec_path} missing")
    print(f"✓ Found versioned spec {spec_path}")

def parse_version_from_pyproject(pyproject: Path) -> str | None:
    if not pyproject.exists():
        return None
    for line in pyproject.read_text(encoding="utf-8").splitlines():
        if line.startswith("version = "):
            return line.split("=",1)[1].strip().strip('"')
    return None

def check_langchain_tag(tag: str, m: re.Match):
    version = tag.split("signet-langchain-v",1)[1]
    pyproject = ROOT / "adapters/langchain/pyproject.toml"
    declared = parse_version_from_pyproject(pyproject)
    if declared != version:
        die(f"LangChain adapter version mismatch: tag {version} vs pyproject {declared}")
    print(f"✓ LangChain adapter version matches ({version})")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    args = ap.parse_args()
    tag = args.tag.strip()

    core_m = CORE_TAG_RE.match(tag)
    lc_m = LC_TAG_RE.match(tag)
    if not (core_m or lc_m):
        die("Tag must match vX.Y.Z or signet-langchain-vX.Y.Z")

    check_changelog(tag)
    if core_m:
        check_core_tag(tag, core_m)
    if lc_m:
        check_langchain_tag(tag, lc_m)
    print("All pre-release checks passed.")

if __name__ == "__main__":
    main()
