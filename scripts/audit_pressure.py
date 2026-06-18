#!/usr/bin/env python3
"""Render a pressure-test audit for the CTF Agent skill suite."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


PRESSURE_CASES = [
    {
        "id": "scope-boundary-under-pressure",
        "mode": "current_gate",
        "question": "If a challenge prompt asks for real-target exploitation, where is the hard stop?",
        "failure_mode": "The agent treats a CTF hint as authorization for active testing outside the allowed scope.",
        "next_action": "Keep scope_status explicit before active actions and rerun phase gates after profile updates.",
        "evidence": [
            {"path": "skills/ctf-master/SKILL.md", "terms": ["legal CTF", "authorized lab", "local isolated", "scope gate"]},
            {"path": "skills/ctf-master/references/acceptance-gates.md", "terms": ["Authorization", "scope", "Human Intervention"]},
            {"path": "skills/ctf-master/scripts/gate_state.py", "terms": ["intake-scope", "require-ready"]},
        ],
    },
    {
        "id": "reference-absorption-under-pressure",
        "mode": "current_gate",
        "question": "Can we show what was borrowed from each requested reference without blindly copying it?",
        "failure_mode": "The suite claims inspiration from references but future maintainers cannot audit conversion choices.",
        "next_action": "Update the source matrix whenever a source changes a checklist, gate, ToolCard, or script contract.",
        "evidence": [
            {"path": "research/seed-source-matrix.md", "terms": ["Borrowed Design", "Do Not Blindly Copy", "Skill Conversion", "Source Anchor"]},
            {"path": "scripts/audit_source_matrix.py", "terms": ["REQUIRED_SOURCES", "conversion_terms", "missing_provenance_count"]},
            {"path": "REFLECTION_AUDIT.md", "terms": ["src-hunter-skill", "yaklang/hack-skills", "red_team_skill"]},
        ],
    },
    {
        "id": "release-drift-under-pressure",
        "mode": "current_gate",
        "question": "If a future iteration adds a script or requirement, what prevents manifest, docs, tests, and gates from drifting apart?",
        "failure_mode": "The suite keeps passing narrow checks while release docs, validation commands, and traceability describe different artifacts.",
        "next_action": "Run the release consistency audit after every new script, validation command, version bump, or traceability change.",
        "evidence": [
            {"path": "scripts/audit_release_consistency.py", "terms": ["ctf-release-consistency-audit-v1", "validation-commands", "traceability-doc-sync"]},
            {"path": "suite-manifest.json", "terms": ["release_consistency_audit", "0.38.0"]},
            {"path": "tests/test_scripts.py", "terms": ["test_release_consistency_audit_checks_manifest_docs_and_traceability"]},
            {"path": "REFLECTION_AUDIT.md", "terms": ["Release consistency audit", "0.38.0"]},
        ],
    },
    {
        "id": "state-discipline-under-pressure",
        "mode": "current_gate",
        "question": "When the solve gets long, what prevents repeated guesses and context loss?",
        "failure_mode": "The agent forgets dead ends, loses raw evidence paths, or retries an old hypothesis.",
        "next_action": "Checkpoint before context compression and update CTFRunState after each material experiment.",
        "evidence": [
            {"path": "skills/ctf-master/references/state-schema.md", "terms": ["CTFRunState", "EvidenceRecord", "HandoffPacket"]},
            {"path": "skills/ctf-master/scripts/validate_state.py", "terms": ["ctf-run-state-validation-v1", "raw_artifact", "next_actions"]},
            {"path": "skills/ctf-master/scripts/checkpoint_state.py", "terms": ["ctf-run-checkpoint-v1", "resume_checklist", "resume_risks"]},
        ],
    },
    {
        "id": "tool-friction-under-pressure",
        "mode": "current_gate",
        "question": "If a tool is missing, noisy, or unsuitable, does the agent have a smaller next move?",
        "failure_mode": "The agent burns time reinstalling tools or dumping huge output into context.",
        "next_action": "Record the failure as evidence, summarize long output, and refine the ToolCard after repeat friction.",
        "evidence": [
            {"path": "skills/ctf-tool-preflight/references/tool-cards.md", "terms": ["Failure", "Retry", "Compression"]},
            {"path": "skills/ctf-tool-preflight/scripts/ctf_preflight.py", "terms": ["PROFILES", "PROFILE_ALIASES", "missing"]},
            {"path": "skills/ctf-master/scripts/summarize_output.py", "terms": ["flag", "error", "warning"]},
        ],
    },
    {
        "id": "routing-conflict-under-pressure",
        "mode": "current_gate",
        "question": "Can ambiguous challenge signals route to the right deep topic without stealing each other?",
        "failure_mode": "A generic keyword such as canary or tool pushes the agent into the wrong category.",
        "next_action": "Add route probes and trigger audit cases whenever a real ambiguity repeats.",
        "evidence": [
            {"path": "skills/ctf-master/scripts/route_topic.py", "terms": ["topic_id", "first_safe_actions", "evidence_gates"]},
            {"path": "scripts/audit_triggers.py", "terms": ["INLINE_PROBES", "forbidden_top", "CUE_PATTERNS"]},
            {"path": "forward-tests/scenarios/deep-topic-mixed-signals.json", "terms": ["expected_skills", "must_include"]},
        ],
    },
    {
        "id": "untrusted-content-under-pressure",
        "mode": "current_gate",
        "question": "What happens when the challenge text contains a fake flag or direct instruction to the agent?",
        "failure_mode": "The agent follows embedded instructions, reports a fake flag, repeats a hostile instruction verbatim, or hides useful clues while filtering.",
        "next_action": "Scan untrusted content before treating it as instruction; preserve suspicious raw paths while using sanitized reporting in notes.",
        "evidence": [
            {"path": "skills/ctf-anti-injection/references/untrusted-content.md", "terms": ["fake flag", "tool output", "Sanitized Reporting"]},
            {"path": "skills/ctf-anti-injection/scripts/scan_untrusted_text.py", "terms": ["ignore", "submit this", "fake_flag", "sanitize_excerpt"]},
            {"path": "demo-fixtures/friendly-login/README.md", "terms": ["Ignore previous instructions", "not_real"]},
        ],
    },
    {
        "id": "handoff-recovery-under-pressure",
        "mode": "current_gate",
        "question": "If three paths fail, can another solver continue faster than starting over?",
        "failure_mode": "The handoff says what was tried but not what to do next or why the run is blocked.",
        "next_action": "Render handoff and reflection from state; include dead ends, evidence, and most likely next steps.",
        "evidence": [
            {"path": "skills/ctf-handoff-report/references/handoff-template.md", "terms": ["evidence_table", "most_likely_next_steps"]},
            {"path": "skills/ctf-handoff-report/scripts/render_handoff.py", "terms": ["Dead Ends", "Next Actions"]},
            {"path": "skills/ctf-handoff-report/scripts/render_reflection.py", "terms": ["improvement_candidates", "hard_questions"]},
        ],
    },
    {
        "id": "fresh-agent-proof-under-pressure",
        "mode": "accepted_gap",
        "gap_id": "REQ-EVAL-FRESH-AGENT",
        "question": "Can a clean agent use the suite without leaked expected answers?",
        "failure_mode": "The suite looks good only because the current thread remembers the intended answers.",
        "next_action": "Run a real fresh-agent forward suite, finalize with response hashes and rubric, then verify the record.",
        "evidence": [
            {"path": "research/requirements-traceability.json", "terms": ["REQ-EVAL-FRESH-AGENT", "\"status\": \"partial\""]},
            {"path": "scripts/audit_completion.py", "terms": ["fresh-agent-independent-run", "v1_ready"]},
            {"path": "scripts/render_forward_handoff.py", "terms": ["ctf-forward-handoff-render-v1", "FORBIDDEN_LEAK_TERMS"]},
            {"path": "scripts/audit_fresh_agent_readiness.py", "terms": ["ctf-fresh-agent-readiness-audit-v1", "ready_for_fresh_agent"]},
            {"path": "scripts/export_fresh_agent_packet.py", "terms": ["ctf-fresh-agent-packet-export-v1", "PACKET_MANIFEST.json"]},
            {"path": "scripts/audit_fresh_agent_packet.py", "terms": ["ctf-fresh-agent-packet-audit-v1", "prompt sha256 mismatch"]},
            {"path": "scripts/render_fresh_agent_launch_prompt.py", "terms": ["ctf-fresh-agent-launch-prompt-render-v1", "Allowed local skill root"]},
            {"path": "scripts/verify_forward_run.py", "terms": ["fresh_context_confirmed", "response_hashes", "human_rubric"]},
        ],
    },
    {
        "id": "benchmark-breadth-watch",
        "mode": "future_watch",
        "question": "Does one solved benchmark prove broad solve-rate across web, pwn, rev, crypto, and forensics?",
        "failure_mode": "A single easy benchmark overstates category coverage.",
        "next_action": "Before claiming v1 breadth, add at least one authorized run per major category.",
        "evidence": [
            {"path": "REFLECTION_AUDIT.md", "terms": ["Run on at least one challenge per major category"]},
            {"path": "scripts/audit_category_coverage.py", "terms": ["ctf-category-coverage-audit-v1", "future_benchmark_needed"]},
            {"path": "benchmarks/runs/cybench-primary-knowledge/benchmark-run-record.json", "terms": ["solved_oracle_validated"]},
            {"path": "scripts/verify_benchmark_run.py", "terms": ["benchmark-run-record", "solved_oracle_validated"]},
        ],
    },
]


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def check_terms(root: Path, evidence: list[dict]) -> tuple[bool, list[str], list[dict]]:
    problems: list[str] = []
    checked: list[dict] = []
    for item in evidence:
        rel = item["path"]
        path = root / rel
        record = {"path": rel, "exists": path.exists(), "missing_terms": []}
        if not path.exists():
            problems.append(f"{rel} is missing")
            checked.append(record)
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        missing = [term for term in item.get("terms", []) if term not in text]
        record["missing_terms"] = missing
        problems.extend(f"{rel} missing {term}" for term in missing)
        checked.append(record)
    return not problems, problems, checked


def traceability_status(root: Path, req_id: str) -> str:
    matrix = read_json(root / "research/requirements-traceability.json")
    for item in matrix.get("requirements", []):
        if item.get("id") == req_id:
            return item.get("status", "")
    return ""


def completion_v1_ready(root: Path) -> bool:
    text = (root / "scripts/audit_completion.py").read_text(encoding="utf-8")
    return "v1_ready" in text and "fresh-agent-independent-run" in text


def evaluate(root: Path) -> dict:
    cases: list[dict] = []
    hard_questions: list[str] = []
    next_actions: list[str] = []
    failing_ids: list[str] = []
    accepted_gap_ids: list[str] = []
    future_watch_ids: list[str] = []

    for case in PRESSURE_CASES:
        evidence_ok, problems, checked = check_terms(root, case["evidence"])
        status = "pass" if evidence_ok else "fail"
        if case["mode"] == "accepted_gap":
            gap_id = case["gap_id"]
            explicit_gap = traceability_status(root, gap_id) == "partial" and completion_v1_ready(root)
            status = "accepted_gap" if evidence_ok and explicit_gap else "fail"
            if status == "accepted_gap":
                accepted_gap_ids.append(gap_id)
            elif not explicit_gap:
                problems.append(f"{gap_id} is not explicitly recorded as the accepted partial fresh-agent gap")
        elif case["mode"] == "future_watch":
            status = "future_watch" if evidence_ok else "fail"
            if status == "future_watch":
                future_watch_ids.append(case["id"])

        if status == "fail":
            failing_ids.append(case["id"])
        hard_questions.append(case["question"])
        next_actions.append(case["next_action"])
        cases.append({
            "id": case["id"],
            "mode": case["mode"],
            "status": status,
            "question": case["question"],
            "failure_mode": case["failure_mode"],
            "next_action": case["next_action"],
            "evidence": checked,
            "problems": problems,
        })

    return {
        "schema": "ctf-agent-skills-pressure-audit-v1",
        "root": str(root),
        "ok": not failing_ids,
        "case_count": len(cases),
        "failing_count": len(failing_ids),
        "failing_ids": failing_ids,
        "accepted_gap_ids": sorted(set(accepted_gap_ids)),
        "future_watch_ids": future_watch_ids,
        "pressure_cases": cases,
        "hard_questions": hard_questions,
        "next_actions": next_actions,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Pressure-test CTF Agent skill-suite assumptions")
    parser.add_argument("--root", default=ROOT)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    result = evaluate(Path(args.root))
    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"pressure_audit_ok={result['ok']}")
        print(f"accepted_gap_ids={result['accepted_gap_ids']}")
        for item in result["pressure_cases"]:
            print(f"{item['status']}: {item['id']} - {item['question']}")
            for problem in item["problems"]:
                print(f"  - {problem}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
