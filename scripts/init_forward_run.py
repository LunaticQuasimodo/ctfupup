#!/usr/bin/env python3
"""Create a clean workspace for an independent fresh-agent forward test."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
from typing import Any

from audit_forward_integrity import audit_forward_integrity
from render_forward_handoff import build_handoff
from render_forward_rubric import build_rubric_template
from run_forward_suite import DEFAULT_SCENARIOS, load_scenarios, write_prompt_pack


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "suite-manifest.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def suite_version(root: Path) -> str:
    manifest = json.loads((root / "suite-manifest.json").read_text(encoding="utf-8"))
    return str(manifest.get("version", "unknown"))


def build_record(run_id: str, agent_or_model: str, suite_ver: str, prompt_pack_dir: Path, response_dir: Path, score_path: Path, manifest_path: Path, rubric_template_path: Path, fresh_agent_handoff_path: Path) -> dict[str, Any]:
    return {
        "schema": "ctf-forward-run-record-v1",
        "run_id": run_id,
        "date": dt.date.today().isoformat(),
        "agent_or_model": agent_or_model,
        "suite_version": suite_ver,
        "fresh_context_confirmed": False,
        "fork_context": False,
        "expected_answers_disclosed": False,
        "prompt_pack_dir": str(prompt_pack_dir),
        "response_dir": str(response_dir),
        "score_summary_path": str(score_path),
        "workspace_manifest_path": str(manifest_path),
        "rubric_template_path": str(rubric_template_path),
        "fresh_agent_handoff_path": str(fresh_agent_handoff_path),
        "run_log_path": str((ROOT / "forward-tests" / "RUN_LOG.md").resolve()),
        "human_rubric": {
            "completed": False,
            "minimum_total_met": False,
            "no_untrusted_content_zero": False,
            "scenario_scores": [],
        },
        "pass_fail": "not_run",
        "regression_observed": "",
        "skill_changes_proposed": [],
        "toolcard_reference_updates_proposed": [],
        "anti_injection_updates_proposed": [],
    }


def render_runbook(run_id: str, prompt_pack_dir: Path, response_dir: Path, score_path: Path, record_path: Path, rubric_template_path: Path, fresh_agent_handoff_path: Path) -> str:
    return "\n".join([
        f"# Fresh-Agent Forward Run: {run_id}",
        "",
        "Use this workspace to run an independent forward test without exposing expected answers.",
        "",
        "## Inputs",
        "",
        f"- Prompt pack: `{prompt_pack_dir}`",
        f"- Response directory: `{response_dir}`",
        f"- Score output: `{score_path}`",
        f"- Run record: `{record_path}`",
        f"- Rubric template: `{rubric_template_path}`",
        f"- Fresh-agent handoff: `{fresh_agent_handoff_path}`",
        "",
        "## Procedure",
        "",
        "1. Start a fresh agent or thread with no skill-development context.",
        f"2. Give the fresh agent `{fresh_agent_handoff_path}` and then each `*.prompt.txt` file. Pass only the prompt text and the local skill path named inside it.",
        "3. Save each response as `<scenario-id>.md` in the response directory.",
        "4. Score responses:",
        "",
        f"```bash\npython3 scripts/run_forward_suite.py --responses-dir {response_dir} --out {score_path} --json\n```",
        "",
        f"5. Copy and fill the rubric template at `{rubric_template_path}`. Set `completed`, `minimum_total_met`, `no_untrusted_content_zero`, each scenario `total`, and each scenario `pass` only after reviewing the fresh-agent responses.",
        "6. Finalize the run record and response hashes:",
        "",
        f"```bash\npython3 scripts/finalize_forward_run.py {record_path} --agent-or-model <fresh-agent-name> --confirm-fresh-context --rubric-json <rubric.json> --json\n```",
        "",
        "7. Verify the record:",
        "",
        f"```bash\npython3 scripts/verify_forward_run.py {record_path} --json\n```",
        "",
        "Do not give the fresh agent scenario JSON, expected-behavior.md, score output, intended answers, or prior analysis.",
        "",
    ]) + "\n"


def init_forward_run(root: Path, out_dir: Path, run_id: str, agent_or_model: str, scenarios_dir: Path) -> dict[str, Any]:
    out_dir = out_dir.resolve()
    prompt_pack_dir = out_dir / "prompt-pack"
    response_dir = out_dir / "responses"
    score_path = out_dir / "score-summary.json"
    record_path = out_dir / "fresh-agent-run-record.json"
    manifest_path = out_dir / "forward-run-workspace.json"
    runbook_path = out_dir / "RUNBOOK.md"
    rubric_template_path = out_dir / "rubric-template.json"
    fresh_agent_handoff_path = out_dir / "FRESH_AGENT_HANDOFF.md"

    scenarios = load_scenarios(scenarios_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    response_dir.mkdir(parents=True, exist_ok=True)
    prompt_files = write_prompt_pack(scenarios, prompt_pack_dir)
    integrity = audit_forward_integrity(root, scenarios_dir, prompt_pack_dir)

    suite_ver = suite_version(root)
    rubric_template = build_rubric_template(scenarios, run_id, agent_or_model)
    rubric_template_path.write_text(json.dumps(rubric_template, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    record = build_record(run_id, agent_or_model, suite_ver, prompt_pack_dir, response_dir, score_path, manifest_path, rubric_template_path, fresh_agent_handoff_path)
    record_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    runbook_path.write_text(render_runbook(run_id, prompt_pack_dir, response_dir, score_path, record_path, rubric_template_path, fresh_agent_handoff_path), encoding="utf-8")

    prompt_hashes = [
        {
            "scenario_id": path.name.removesuffix(".prompt.txt"),
            "path": str(path),
            "sha256": sha256_file(path),
        }
        for path in sorted(prompt_files)
    ]
    workspace = {
        "schema": "ctf-forward-run-workspace-v1",
        "run_id": run_id,
        "suite_version": suite_ver,
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "scenario_count": len(scenarios),
        "prompt_pack_dir": str(prompt_pack_dir),
        "response_dir": str(response_dir),
        "score_summary_path": str(score_path),
        "record_path": str(record_path),
        "runbook_path": str(runbook_path),
        "rubric_template_path": str(rubric_template_path),
        "fresh_agent_handoff_path": str(fresh_agent_handoff_path),
        "integrity_audit_ok": integrity["ok"],
        "prompt_hashes": prompt_hashes,
    }
    manifest_path.write_text(json.dumps(workspace, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    fresh_agent_handoff_path.write_text(build_handoff(workspace), encoding="utf-8")

    return {
        "schema": "ctf-forward-run-init-v1",
        "ok": integrity["ok"],
        "workspace": str(out_dir),
        "manifest": str(manifest_path),
        "record": str(record_path),
        "runbook": str(runbook_path),
        "rubric_template": str(rubric_template_path),
        "fresh_agent_handoff": str(fresh_agent_handoff_path),
        "prompt_pack_dir": str(prompt_pack_dir),
        "response_dir": str(response_dir),
        "score_summary_path": str(score_path),
        "scenario_count": len(scenarios),
        "prompt_count": len(prompt_files),
        "suite_version": suite_ver,
        "integrity_problems": integrity["problems"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize a fresh-agent forward-test workspace")
    parser.add_argument("--root", default=ROOT)
    parser.add_argument("--scenarios-dir", default=DEFAULT_SCENARIOS)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--run-id", default=f"forward-{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%d-%H%M%S')}")
    parser.add_argument("--agent-or-model", default="pending-fresh-agent")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    scenarios_dir = Path(args.scenarios_dir)
    if not scenarios_dir.is_absolute():
        scenarios_dir = root / scenarios_dir
    result = init_forward_run(root, Path(args.out_dir), args.run_id, args.agent_or_model, scenarios_dir)
    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"forward_run_init_ok={result['ok']}")
        print(f"workspace={result['workspace']}")
        print(f"record={result['record']}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
