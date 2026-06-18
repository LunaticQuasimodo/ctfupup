#!/usr/bin/env python3
"""Package a CTFRunState into validation, checkpoint, handoff, writeup, and reflection artifacts."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import subprocess
import sys
from pathlib import Path


SUITE_ROOT = Path(__file__).resolve().parents[3]
VALIDATE_STATE = SUITE_ROOT / "skills" / "ctf-master" / "scripts" / "validate_state.py"
CHECKPOINT_STATE = SUITE_ROOT / "skills" / "ctf-master" / "scripts" / "checkpoint_state.py"
RENDER_HANDOFF = Path(__file__).resolve().with_name("render_handoff.py")
RENDER_WRITEUP = Path(__file__).resolve().with_name("render_writeup.py")
RENDER_REFLECTION = Path(__file__).resolve().with_name("render_reflection.py")


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=SUITE_ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


def write_command_output(cmd: list[str], out: Path) -> subprocess.CompletedProcess[str]:
    proc = run(cmd)
    out.write_text(proc.stdout, encoding="utf-8")
    return proc


def default_out_dir(state_path: Path) -> Path:
    stem = state_path.parent.name if state_path.parent.name else state_path.stem
    return state_path.parent / f"{stem}-package"


def package_run(state_path: Path, out_dir: Path, *, strict_artifacts: bool = False, allow_invalid: bool = False) -> dict:
    state_path = state_path.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    state_copy = out_dir / "ctf-state.json"
    validation_path = out_dir / "validation.json"
    checkpoint_path = out_dir / "checkpoint.md"
    handoff_path = out_dir / "handoff.md"
    writeup_path = out_dir / "writeup.md"
    reflection_path = out_dir / "reflection.md"

    shutil.copy2(state_path, state_copy)

    validate_cmd = [sys.executable, str(VALIDATE_STATE), str(state_path), "--json"]
    if strict_artifacts:
        validate_cmd.append("--strict-artifacts")
    validation_proc = write_command_output(validate_cmd, validation_path)
    try:
        validation = json.loads(validation_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        validation = {"ok": False, "errors": ["validation output was not JSON"], "warnings": []}

    render_results = {}
    for label, script, output in [
        ("checkpoint", CHECKPOINT_STATE, checkpoint_path),
        ("handoff", RENDER_HANDOFF, handoff_path),
        ("writeup", RENDER_WRITEUP, writeup_path),
        ("reflection", RENDER_REFLECTION, reflection_path),
    ]:
        cmd = [sys.executable, str(script), str(state_path)]
        if label == "checkpoint" and strict_artifacts:
            cmd.append("--strict-artifacts")
        proc = write_command_output(cmd, output)
        render_results[label] = {"returncode": proc.returncode, "ok": proc.returncode == 0, "path": str(output)}

    ok = validation_proc.returncode == 0 and validation.get("ok") is True and all(item["ok"] for item in render_results.values())
    if allow_invalid and all(item["ok"] for item in render_results.values()):
        ok = True

    state = json.loads(state_path.read_text(encoding="utf-8"))
    challenge = state.get("challenge", {})
    manifest = {
        "schema": "ctf-run-package-v1",
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "ok": ok,
        "source_state": str(state_path),
        "package_dir": str(out_dir),
        "challenge": {
            "title": challenge.get("title", "unknown"),
            "platform": challenge.get("platform", "unknown"),
            "category": challenge.get("category_inferred") or challenge.get("category_claimed", "unknown"),
            "scope_status": challenge.get("scope_status", "unknown"),
        },
        "artifacts": {
            "state": str(state_copy),
            "validation": str(validation_path),
            "checkpoint": str(checkpoint_path),
            "handoff": str(handoff_path),
            "writeup": str(writeup_path),
            "reflection": str(reflection_path),
        },
        "validation_ok": validation.get("ok") is True,
        "validation_errors": validation.get("errors", []),
        "validation_warnings": validation.get("warnings", []),
        "render_results": render_results,
    }
    manifest_path = out_dir / "run-package-manifest.json"
    manifest["manifest"] = str(manifest_path)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Finalize a CTF run into a reproducible package")
    parser.add_argument("state_json")
    parser.add_argument("--out-dir")
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--strict-artifacts", action="store_true")
    parser.add_argument("--allow-invalid", action="store_true", help="Render package even when state validation fails")
    args = parser.parse_args()

    state_path = Path(args.state_json)
    if not state_path.exists():
        print(f"state file does not exist: {state_path}", file=sys.stderr)
        return 1
    state_path = state_path.resolve()
    out_dir = Path(args.out_dir) if args.out_dir else default_out_dir(state_path)
    manifest = package_run(state_path, out_dir, strict_artifacts=args.strict_artifacts, allow_invalid=args.allow_invalid)
    if args.as_json:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
    else:
        print(f"ok={manifest['ok']} package={manifest['package_dir']}")
        for label, path in manifest["artifacts"].items():
            print(f"{label}: {path}")
    return 0 if manifest["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
