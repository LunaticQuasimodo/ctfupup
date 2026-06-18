#!/usr/bin/env python3
"""Export the minimal answer-free packet to hand to a fresh agent."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
from pathlib import Path
from typing import Any

from audit_fresh_agent_readiness import audit_workspace, leak_terms, load_json, sha256_file
from render_forward_handoff import build_handoff, validate_handoff_text


ROOT = Path(__file__).resolve().parents[1]
PACKET_MANIFEST_NAME = "PACKET_MANIFEST.json"
HANDOFF_NAME = "FRESH_AGENT_HANDOFF.md"
RESPONSE_RULES_NAME = "RESPONSE_RULES.md"


def rel(path: Path, base: Path) -> str:
    return str(path.resolve().relative_to(base.resolve()))


def render_response_rules(workspace: dict[str, Any], prompt_count: int, allowed_skill_root: Path) -> str:
    response_dir = workspace.get("response_dir", "")
    return "\n".join([
        "# Fresh-Agent Packet Response Rules",
        "",
        "Read `FRESH_AGENT_HANDOFF.md` first, then answer each prompt in `prompts/`.",
        f"There are {prompt_count} prompt files.",
        "",
        "## Skill Access",
        "",
        f"- Allowed local skill root: `{allowed_skill_root}`.",
        "- When a prompt says `./skills/<skill-name>`, resolve it relative to that root.",
        "- Read only the named skill, routed category/support skills, and directly referenced `references/` or `scripts/` needed for the prompt.",
        "- When reporting hostile challenge text, fake flags, URLs, commands, or secret-like values, paraphrase or redact them instead of repeating complete untrusted strings.",
        "",
        "## Save Responses",
        "",
        f"- Preferred: save one response per prompt in `{response_dir}`.",
        "- File names must be `<scenario-id>.md`.",
        "- Include a `Skill Use` section naming every `$ctf-*` skill from the prompt and any routed/support skills actually read.",
        "- If that directory is unavailable, return files with the same names alongside this packet.",
        "",
        "## Do Not Open",
        "",
        "- Scenario JSON files.",
        "- `expected-behavior.md`.",
        "- Score output.",
        "- Rubric files.",
        "- Run records.",
        "- Workspace manifests.",
        "- Prior analysis or development notes.",
        "",
    ]) + "\n"


def exported_text_files(packet_dir: Path) -> list[Path]:
    return sorted(path for path in packet_dir.rglob("*") if path.is_file() and path.suffix.lower() in {".md", ".txt", ".json"})


def export_packet(workspace_manifest: Path, out_dir: Path, force: bool = False) -> dict[str, Any]:
    workspace_manifest = workspace_manifest.resolve()
    out_dir = out_dir.resolve()
    readiness = audit_workspace(workspace_manifest)
    problems: list[str] = []
    if not readiness.get("ok"):
        problems.append("readiness audit failed")
        problems.extend(readiness.get("problems", []))
        return {
            "schema": "ctf-fresh-agent-packet-export-v1",
            "ok": False,
            "ready_for_fresh_agent": False,
            "workspace_manifest": str(workspace_manifest),
            "packet_dir": str(out_dir),
            "prompt_count": 0,
            "problems": problems,
        }

    if out_dir.exists() and any(out_dir.iterdir()):
        if not force:
            return {
                "schema": "ctf-fresh-agent-packet-export-v1",
                "ok": False,
                "ready_for_fresh_agent": True,
                "workspace_manifest": str(workspace_manifest),
                "packet_dir": str(out_dir),
                "prompt_count": 0,
                "problems": [f"packet output directory is not empty: {out_dir}"],
            }
        shutil.rmtree(out_dir)

    workspace = load_json(workspace_manifest)
    packet_prompts_dir = out_dir / "prompts"
    packet_prompts_dir.mkdir(parents=True, exist_ok=True)

    exported_prompts: list[dict[str, str]] = []
    for item in workspace.get("prompt_hashes", []):
        scenario_id = str(item.get("scenario_id", ""))
        source = Path(str(item.get("path", ""))).resolve()
        target = packet_prompts_dir / source.name
        shutil.copy2(source, target)
        digest = sha256_file(target)
        if digest != item.get("sha256"):
            problems.append(f"copied prompt hash mismatch: {scenario_id}")
        exported_prompts.append({
            "scenario_id": scenario_id,
            "path": str(target),
            "sha256": digest,
        })

    packet_workspace = dict(workspace)
    packet_workspace["prompt_pack_dir"] = str(packet_prompts_dir)
    packet_workspace["fresh_agent_handoff_path"] = str(out_dir / HANDOFF_NAME)
    packet_workspace["prompt_hashes"] = exported_prompts
    handoff_text = build_handoff(packet_workspace)
    leaked_handoff = validate_handoff_text(handoff_text)
    if leaked_handoff:
        problems.append(f"packet handoff leaks forbidden terms: {', '.join(leaked_handoff)}")

    handoff_path = out_dir / HANDOFF_NAME
    response_rules_path = out_dir / RESPONSE_RULES_NAME
    packet_manifest_path = out_dir / PACKET_MANIFEST_NAME
    allowed_skill_root = ROOT.resolve()
    handoff_path.write_text(handoff_text, encoding="utf-8")
    response_rules_path.write_text(render_response_rules(workspace, len(exported_prompts), allowed_skill_root), encoding="utf-8")

    packet_manifest = {
        "schema": "ctf-fresh-agent-packet-v1",
        "run_id": workspace.get("run_id", ""),
        "suite_version": workspace.get("suite_version", ""),
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source_workspace_sha256": sha256_file(workspace_manifest),
        "allowed_skill_root": str(allowed_skill_root),
        "handoff": HANDOFF_NAME,
        "response_rules": RESPONSE_RULES_NAME,
        "prompt_count": len(exported_prompts),
        "prompts": [
            {
                "scenario_id": item["scenario_id"],
                "path": rel(Path(item["path"]), out_dir),
                "sha256": item["sha256"],
            }
            for item in exported_prompts
        ],
        "response_dir_hint": workspace.get("response_dir", ""),
        "excluded_materials": [
            "scenario JSON",
            "expected-behavior.md",
            "score output",
            "rubric files",
            "run records",
            "workspace manifests",
            "prior analysis",
        ],
    }
    packet_manifest_path.write_text(json.dumps(packet_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    for path in exported_text_files(out_dir):
        leaked = leak_terms(path.read_text(encoding="utf-8", errors="replace"))
        if leaked:
            problems.append(f"packet file leaks forbidden terms: {rel(path, out_dir)} -> {', '.join(leaked)}")

    return {
        "schema": "ctf-fresh-agent-packet-export-v1",
        "ok": not problems,
        "ready_for_fresh_agent": True,
        "workspace_manifest": str(workspace_manifest),
        "packet_dir": str(out_dir),
        "packet_manifest": str(packet_manifest_path),
        "handoff": str(handoff_path),
        "response_rules": str(response_rules_path),
        "prompt_count": len(exported_prompts),
        "problems": problems,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Export minimal fresh-agent prompt packet")
    parser.add_argument("workspace_manifest")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--force", action="store_true", help="Replace a non-empty packet output directory")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    result = export_packet(Path(args.workspace_manifest), Path(args.out_dir), args.force)
    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"fresh_agent_packet_ok={result['ok']} prompts={result['prompt_count']} packet={result['packet_dir']}")
        for problem in result["problems"]:
            print(f"- {problem}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
