#!/usr/bin/env python3
"""Run the local release gate for the CTF Agent skill suite."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ALLOWED_PARTIAL_OR_OPEN = {"REQ-EVAL-FRESH-AGENT"}
RESIDUE_RE = re.compile(
    r"TODO|\[TODO|Structuring This Skill|Resources \(optional\)|description: \[|lorem|placeholder",
    re.I,
)
RESIDUE_SCAN_EXCLUDE = {
    "scripts/release_gate.py",
    "scripts/validate_suite.py",
}


def run_command(cmd: list[str]) -> dict:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    proc = subprocess.run(
        cmd,
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return {
        "cmd": cmd,
        "returncode": proc.returncode,
        "ok": proc.returncode == 0,
        "stdout": proc.stdout,
    }


def scan_residue(root: Path) -> dict:
    matches = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        rel_text = str(rel)
        if ".git" in path.parts or "__pycache__" in path.parts or rel_text in RESIDUE_SCAN_EXCLUDE:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            if RESIDUE_RE.search(line):
                matches.append({"path": rel_text, "line": lineno, "text": line[:200]})
    return {"ok": not matches, "matches": matches}


def check_traceability(raw: str) -> dict:
    data = json.loads(raw)
    partial = set(data.get("partial_or_open_ids", []))
    unexpected = sorted(partial - ALLOWED_PARTIAL_OR_OPEN)
    missing_expected = sorted(ALLOWED_PARTIAL_OR_OPEN - partial)
    return {
        "ok": data.get("failing_count") == 0 and not unexpected and not missing_expected,
        "requirements_checked": data.get("requirements_checked"),
        "failing_count": data.get("failing_count"),
        "partial_or_open_ids": sorted(partial),
        "unexpected_partial_or_open": unexpected,
        "missing_expected_partial_or_open": missing_expected,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run local release gate")
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--skip-unittest", action="store_true", help="Skip unit tests to avoid recursive test harness calls")
    args = parser.parse_args()

    run_root = Path(tempfile.mkdtemp(prefix="ctf-agent-skills-release-"))
    commands = [
        [sys.executable, "scripts/validate_suite.py", "--smoke"],
        [sys.executable, "scripts/audit_completion.py", "--json"],
        [sys.executable, "scripts/audit_quality.py", "--json"],
        [sys.executable, "scripts/audit_pressure.py", "--json"],
        [sys.executable, "scripts/audit_category_coverage.py", "--json"],
        [sys.executable, "scripts/audit_evidence_contract.py", "--json"],
        [sys.executable, "scripts/audit_release_consistency.py", "--json"],
        [sys.executable, "scripts/audit_source_matrix.py", "--json"],
        [sys.executable, "scripts/audit_agent_metadata.py", "--json"],
        [sys.executable, "scripts/audit_triggers.py", "--json"],
        [sys.executable, "scripts/audit_traceability.py", "--json"],
        [sys.executable, "scripts/verify_benchmark_run.py", "benchmarks/runs/cybench-primary-knowledge", "--json"],
        [sys.executable, "skills/ctf-master/scripts/gate_state.py", "benchmarks/runs/cybench-primary-knowledge/ctf-state.json", "--require-ready", "report", "--strict-artifacts", "--json"],
        [sys.executable, "skills/ctf-master/scripts/checkpoint_state.py", "benchmarks/runs/cybench-primary-knowledge/ctf-state.json", "--json", "--strict-artifacts"],
        [sys.executable, "scripts/run_demo_solve.py", "--all", "--out-dir", str(run_root / "demo")],
        [sys.executable, "scripts/audit_forward_integrity.py", "--json"],
        [sys.executable, "scripts/render_forward_rubric.py", "--run-id", "release-forward-rubric", "--out", str(run_root / "forward-rubric.json"), "--json"],
        [sys.executable, "scripts/init_forward_run.py", "--run-id", "release-forward-init", "--out-dir", str(run_root / "forward-init"), "--json"],
        [sys.executable, "scripts/render_forward_handoff.py", str(run_root / "forward-init" / "forward-run-workspace.json"), "--out", str(run_root / "forward-handoff.md"), "--json"],
        [sys.executable, "scripts/audit_fresh_agent_readiness.py", str(run_root / "forward-init" / "forward-run-workspace.json"), "--json"],
        [sys.executable, "scripts/export_fresh_agent_packet.py", str(run_root / "forward-init" / "forward-run-workspace.json"), "--out-dir", str(run_root / "fresh-agent-packet"), "--json"],
        [sys.executable, "scripts/audit_fresh_agent_packet.py", str(run_root / "fresh-agent-packet"), "--json"],
        [sys.executable, "scripts/render_fresh_agent_launch_prompt.py", str(run_root / "fresh-agent-packet"), "--out", str(run_root / "fresh-agent-launch-prompt.md"), "--json"],
        [sys.executable, "scripts/run_forward_suite.py", "--list", "--json"],
    ]
    if not args.skip_unittest:
        commands.insert(0, [sys.executable, "-m", "unittest", "discover", "-s", "tests"])
    command_results = [run_command(cmd) for cmd in commands]
    residue = scan_residue(ROOT)

    traceability = {"ok": False, "error": "traceability command did not run"}
    for item in command_results:
        if item["cmd"][1].endswith("audit_traceability.py") and item["ok"]:
            try:
                traceability = check_traceability(item["stdout"])
            except Exception as exc:  # pragma: no cover - defensive
                traceability = {"ok": False, "error": str(exc)}

    ok = all(item["ok"] for item in command_results) and residue["ok"] and traceability["ok"]
    result = {
        "schema": "ctf-agent-skills-release-gate-v1",
        "ok": ok,
        "run_root": str(run_root),
        "allowed_partial_or_open": sorted(ALLOWED_PARTIAL_OR_OPEN),
        "traceability": traceability,
        "residue_scan": residue,
        "commands": command_results,
    }
    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"release_gate_ok={ok}")
        print(f"partial_or_open={traceability.get('partial_or_open_ids', [])}")
        if not residue["ok"]:
            print(f"residue_matches={len(residue['matches'])}")
        for item in command_results:
            status = "ok" if item["ok"] else "fail"
            print(f"{status}: {' '.join(item['cmd'])}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
