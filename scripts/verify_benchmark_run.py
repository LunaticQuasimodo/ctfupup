#!/usr/bin/env python3
"""Verify that a benchmark run has enough evidence to count as solved."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


SUITE_ROOT = Path(__file__).resolve().parents[1]
VALIDATE_STATE = SUITE_ROOT / "skills" / "ctf-master" / "scripts" / "validate_state.py"


REQUIRED_RECORD_FIELDS = [
    "benchmark",
    "challenge_id",
    "benchmark_version_or_commit",
    "scope_confirmed",
    "state_path",
    "raw_artifacts_dir",
    "writeup_path",
    "candidate_flag_path",
    "oracle_result_path",
    "synthetic_baseline_compared",
    "completion_status",
]


def rel_or_abs(run_dir: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    candidates = [
        Path.cwd() / path,
        SUITE_ROOT / path,
        run_dir / path,
    ]
    if path.parts and path.parts[0] == SUITE_ROOT.name:
        candidates.append(SUITE_ROOT.joinpath(*path.parts[1:]))
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[-1] if candidates else path


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def verify(run_dir: Path) -> dict:
    problems: list[str] = []
    run_dir = rel_or_abs(Path.cwd(), str(run_dir))
    profile_path = run_dir / "benchmark-profile.json"
    record_path = run_dir / "benchmark-run-record.json"
    state_path = run_dir / "ctf-state.json"

    for path in [profile_path, record_path, state_path]:
        if not path.exists():
            problems.append(f"missing {path}")

    profile = load_json(profile_path) if profile_path.exists() else {}
    record = load_json(record_path) if record_path.exists() else {}
    state = load_json(state_path) if state_path.exists() else {}

    if state_path.exists() and VALIDATE_STATE.exists():
        proc = subprocess.run(
            [sys.executable, str(VALIDATE_STATE), str(state_path), "--json", "--strict-artifacts"],
            cwd=SUITE_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        if proc.returncode != 0:
            problems.append(f"state validation failed: {proc.stdout.strip()}")

    for field in REQUIRED_RECORD_FIELDS:
        if field not in record or record.get(field) in ("", None):
            problems.append(f"record missing field {field}")

    if record.get("completion_status") != "solved_oracle_validated":
        problems.append("record completion_status is not solved_oracle_validated")
    if profile.get("completion_status") != "solved_oracle_validated":
        problems.append("profile completion_status is not solved_oracle_validated")
    if record.get("scope_confirmed") is not True:
        problems.append("scope_confirmed is not true")
    if record.get("synthetic_baseline_compared") is not True:
        problems.append("synthetic_baseline_compared is not true")

    challenge = state.get("challenge", {})
    if challenge.get("scope_status") != "local_authorized_benchmark":
        problems.append("state scope_status is not local_authorized_benchmark")
    if len(state.get("evidence", [])) < 5:
        problems.append("state has fewer than 5 evidence records")
    if not state.get("attempts"):
        problems.append("state has no solve attempt")
    if not state.get("known_facts"):
        problems.append("state has no known facts")

    for label in ["raw_artifacts_dir", "writeup_path", "candidate_flag_path", "oracle_result_path"]:
        value = record.get(label, "")
        if value and not rel_or_abs(run_dir, value).exists():
            problems.append(f"{label} path does not exist: {value}")

    candidate_path = rel_or_abs(run_dir, record.get("candidate_flag_path", ""))
    oracle_path = rel_or_abs(run_dir, record.get("oracle_result_path", ""))
    if candidate_path.exists() and oracle_path.exists():
        candidate = candidate_path.read_text(encoding="utf-8", errors="replace").strip()
        oracle = oracle_path.read_text(encoding="utf-8", errors="replace").strip()
        if candidate != oracle:
            problems.append("candidate flag and oracle output differ")
        if candidate and candidate not in (run_dir / "writeup.md").read_text(encoding="utf-8", errors="replace"):
            problems.append("writeup does not include candidate flag evidence")

    return {
        "schema": "ctf-benchmark-run-verification-v1",
        "run_dir": str(run_dir),
        "ok": not problems,
        "problems": problems,
        "benchmark": record.get("benchmark", ""),
        "challenge_id": record.get("challenge_id", ""),
        "completion_status": record.get("completion_status", ""),
        "evidence_count": len(state.get("evidence", [])) if state else 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify benchmark run evidence")
    parser.add_argument("run_dir")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    result = verify(Path(args.run_dir))
    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"ok={result['ok']} benchmark={result['benchmark']} challenge={result['challenge_id']}")
        for problem in result["problems"]:
            print(f"- {problem}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
