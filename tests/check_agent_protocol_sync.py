#!/usr/bin/env python3
"""Drift check for the vendored agent_protocol across suite MCP servers.

Each suite server ships the protocol as its own DEFAULT_AGENT_PROTOCOL constant
(mcp_server/schemas/config.py) so it stays self-contained for other labs. This
check fails if any server's constant has drifted from the canonical source
docs/authoring/agent_protocol.txt (compared whitespace-normalized). It is a
morphic-dev hygiene check, not a runtime dependency.

Suites whose checkout is absent are skipped (so it never fails spuriously on a
host that only has one suite). Override locations with STAR_SUITE_DIR /
CHROMAP_SUITE_DIR. Exit 0 = in sync (or nothing to compare), 1 = drift.
"""
from __future__ import annotations
import ast
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CANON = REPO / "docs/authoring/agent_protocol.txt"
SUITES = {
    "STAR-suite": os.environ.get("STAR_SUITE_DIR", "/mnt/pikachu/STAR-suite"),
    "Chromap-suite": os.environ.get("CHROMAP_SUITE_DIR", "/mnt/pikachu/Chromap-suite"),
}


def norm(s: str) -> str:
    return " ".join(s.split())


def canonical() -> str:
    lines = [l for l in CANON.read_text().splitlines() if not l.lstrip().startswith("#")]
    return norm(" ".join(lines))


def extract_default(config_py: Path):
    tree = ast.parse(config_py.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == "DEFAULT_AGENT_PROTOCOL":
                    try:
                        return ast.literal_eval(node.value)
                    except Exception:
                        return None
    return None


def main() -> int:
    if not CANON.exists():
        print(f"FAIL: canonical missing: {CANON}")
        return 1
    want = canonical()
    rc = 0
    checked = 0
    for name, d in SUITES.items():
        cfg = Path(d) / "mcp_server/schemas/config.py"
        if not cfg.exists():
            print(f"  SKIP {name}: {cfg} absent")
            continue
        got = extract_default(cfg)
        if got is None:
            print(f"  FAIL {name}: DEFAULT_AGENT_PROTOCOL not found / not a literal")
            rc = 1
            continue
        checked += 1
        if norm(got) == want:
            print(f"  PASS {name}: matches canonical agent_protocol.txt")
        else:
            print(f"  FAIL {name}: DEFAULT_AGENT_PROTOCOL drifts from canonical")
            rc = 1
    if checked == 0:
        print("  (no suite checkouts present — nothing compared)")
    print("ALL PASS" if rc == 0 else "DRIFT DETECTED")
    return rc


if __name__ == "__main__":
    sys.exit(main())
