#!/usr/bin/env python3
"""Audit category coverage across routing, skills, demos, forward tests, and benchmarks."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

CATEGORY_SPECS: dict[str, dict[str, Any]] = {
    "web": {
        "kind": "core",
        "skill": "ctf-web",
        "topic_prefixes": ["web."],
        "reference_terms": ["Endpoint Matrix", "White-Box Audit Order"],
        "reference_paths": ["skills/ctf-web/references/web-triage.md"],
        "demo_fixtures": ["friendly-login"],
        "forward_terms": ["ctf-web"],
    },
    "pwn": {
        "kind": "core",
        "skill": "ctf-pwn-rev",
        "topic_prefixes": ["pwn."],
        "reference_terms": ["Pwn Questions", "Offset known"],
        "reference_paths": ["skills/ctf-pwn-rev/references/pwn-rev-triage.md"],
        "demo_fixtures": ["pwn-offset"],
        "forward_terms": ["pwn challenge"],
    },
    "reverse": {
        "kind": "core",
        "skill": "ctf-pwn-rev",
        "topic_prefixes": ["rev."],
        "reference_terms": ["Reverse Questions", "Reverse key recovered"],
        "reference_paths": ["skills/ctf-pwn-rev/references/pwn-rev-triage.md"],
        "demo_fixtures": ["reverse-rot13"],
        "forward_terms": ["rev.checker"],
    },
    "crypto": {
        "kind": "core",
        "skill": "ctf-forensics-crypto",
        "topic_prefixes": ["crypto."],
        "reference_terms": ["Attack-Condition Routing", "Verification"],
        "reference_paths": ["skills/ctf-forensics-crypto/references/crypto-triage.md"],
        "demo_fixtures": ["crypto-xor"],
        "forward_terms": ["crypto.rsa"],
        "benchmark_categories": ["crypto"],
    },
    "forensics": {
        "kind": "core",
        "skill": "ctf-forensics-crypto",
        "topic_prefixes": ["forensics."],
        "reference_terms": ["Universal First Pass", "Preserve Evidence"],
        "reference_paths": ["skills/ctf-forensics-crypto/references/forensics-triage.md"],
        "demo_fixtures": ["forensics-b64log"],
        "forward_terms": ["pcap", "forensics"],
    },
    "specialty-ai": {
        "kind": "specialty",
        "skill": "ctf-specialty",
        "topic_ids": ["specialty.ai-tool"],
        "reference_terms": ["AI/LLM Security", "challenge-provided canaries"],
        "reference_paths": ["skills/ctf-specialty/references/specialty-triage.md"],
        "forward_terms": ["ctf-specialty", "AI/LLM", "canary"],
    },
    "specialty-blockchain": {
        "kind": "specialty",
        "skill": "ctf-specialty",
        "topic_ids": ["specialty.blockchain"],
        "reference_terms": ["Blockchain", "tx hash"],
        "reference_paths": ["skills/ctf-specialty/references/specialty-triage.md"],
        "forward_terms": [],
    },
    "specialty-mobile": {
        "kind": "specialty",
        "skill": "ctf-specialty",
        "topic_ids": ["specialty.mobile"],
        "reference_terms": ["Mobile", "APK/IPA"],
        "reference_paths": ["skills/ctf-specialty/references/specialty-triage.md"],
        "forward_terms": [],
    },
    "specialty-cloud": {
        "kind": "specialty",
        "skill": "ctf-specialty",
        "topic_ids": ["specialty.cloud-k8s"],
        "reference_terms": ["Cloud/K8s/Container", "RBAC"],
        "reference_paths": ["skills/ctf-specialty/references/specialty-triage.md"],
        "forward_terms": [],
    },
}


def load_route_topics(root: Path) -> list[dict[str, Any]]:
    route_path = root / "skills/ctf-master/scripts/route_topic.py"
    if not route_path.exists():
        return []
    spec = importlib.util.spec_from_file_location("ctf_route_topic_for_coverage", route_path)
    if not spec or not spec.loader:
        return []
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return list(getattr(module, "TOPICS", []))


def load_manifest_skills(root: Path) -> set[str]:
    path = root / "suite-manifest.json"
    if not path.exists():
        return set()
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return set()
    return {item.get("name", "") for item in manifest.get("skills", [])}


def load_forward_scenarios(root: Path) -> list[dict[str, Any]]:
    scenarios = []
    for path in sorted((root / "forward-tests/scenarios").glob("*.json")):
        try:
            item = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        item["_path"] = str(path.relative_to(root))
        scenarios.append(item)
    return scenarios


def load_demo_fixtures(root: Path) -> set[str]:
    demo_root = root / "demo-fixtures"
    if not demo_root.exists():
        return set()
    return {path.name for path in demo_root.iterdir() if path.is_dir()}


def load_benchmark_categories(root: Path) -> dict[str, list[str]]:
    categories: dict[str, list[str]] = {}
    for record_path in sorted((root / "benchmarks/runs").glob("*/benchmark-run-record.json")):
        try:
            record = json.loads(record_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if record.get("completion_status") != "solved_oracle_validated":
            continue
        category = str(record.get("category", ""))
        if not category:
            continue
        categories.setdefault(category, []).append(str(record_path.relative_to(root)))
    return categories


def scenario_matches(scenario: dict[str, Any], terms: list[str]) -> bool:
    if not terms:
        return False
    text_parts = [
        scenario.get("id", ""),
        scenario.get("title", ""),
        scenario.get("prompt", ""),
        " ".join(scenario.get("expected_skills", [])),
        " ".join(scenario.get("must_include", [])),
    ]
    text = "\n".join(text_parts).lower()
    return all(term.lower() in text for term in terms[:1]) or any(term.lower() in text for term in terms)


def reference_check(root: Path, paths: list[str], terms: list[str]) -> tuple[bool, list[str]]:
    problems: list[str] = []
    found_text = ""
    for rel in paths:
        path = root / rel
        if not path.exists():
            problems.append(f"missing reference {rel}")
            continue
        found_text += "\n" + path.read_text(encoding="utf-8", errors="replace")
    for term in terms:
        if term not in found_text:
            problems.append(f"missing reference term {term}")
    return not problems, problems


def evaluate_category(
    root: Path,
    category_id: str,
    spec: dict[str, Any],
    manifest_skills: set[str],
    topics: list[dict[str, Any]],
    demo_fixtures: set[str],
    forward_scenarios: list[dict[str, Any]],
    benchmark_categories: dict[str, list[str]],
) -> dict[str, Any]:
    problems: list[str] = []
    skill = spec["skill"]
    skill_present = skill in manifest_skills and (root / "skills" / skill / "SKILL.md").exists()
    if not skill_present:
        problems.append(f"missing skill {skill}")

    topic_ids = {item.get("topic_id", "") for item in topics}
    expected_topic_ids = set(spec.get("topic_ids", []))
    prefixes = spec.get("topic_prefixes", [])
    matched_topics = sorted(
        item.get("topic_id", "")
        for item in topics
        if item.get("topic_id") in expected_topic_ids or any(str(item.get("topic_id", "")).startswith(prefix) for prefix in prefixes)
    )
    for topic_id in expected_topic_ids:
        if topic_id not in topic_ids:
            problems.append(f"missing route topic {topic_id}")
    if prefixes and not matched_topics:
        problems.append(f"missing route topic with prefix {prefixes}")

    refs_ok, ref_problems = reference_check(root, spec.get("reference_paths", []), spec.get("reference_terms", []))
    problems.extend(ref_problems)

    required_demo = spec.get("demo_fixtures", [])
    present_demos = sorted(name for name in required_demo if name in demo_fixtures)
    if spec["kind"] == "core":
        for demo in required_demo:
            if demo not in demo_fixtures:
                problems.append(f"missing demo fixture {demo}")

    forward_matches = [scenario["_path"] for scenario in forward_scenarios if scenario_matches(scenario, spec.get("forward_terms", []))]
    benchmark_matches = []
    for bench_category in spec.get("benchmark_categories", []):
        benchmark_matches.extend(benchmark_categories.get(bench_category, []))
    if spec["kind"] == "core" and not (present_demos or forward_matches or benchmark_matches):
        problems.append("core category has no demo, forward scenario, or benchmark evidence")
    if spec["kind"] == "specialty" and category_id == "specialty-ai" and not forward_matches:
        problems.append("specialty-ai should have a forward scenario because it is adversarial-agent specific")

    return {
        "id": category_id,
        "kind": spec["kind"],
        "skill": skill,
        "ok": not problems,
        "skill_present": skill_present,
        "route_topics": matched_topics,
        "references_ok": refs_ok,
        "demo_fixtures": present_demos,
        "forward_scenarios": sorted(forward_matches),
        "benchmark_runs": sorted(benchmark_matches),
        "problems": problems,
    }


def audit_category_coverage(root: Path) -> dict[str, Any]:
    manifest_skills = load_manifest_skills(root)
    topics = load_route_topics(root)
    demos = load_demo_fixtures(root)
    scenarios = load_forward_scenarios(root)
    benchmarks = load_benchmark_categories(root)
    categories = [
        evaluate_category(root, category_id, spec, manifest_skills, topics, demos, scenarios, benchmarks)
        for category_id, spec in CATEGORY_SPECS.items()
    ]
    failing = [item for item in categories if not item["ok"]]
    core_without_benchmark = [
        item["id"]
        for item in categories
        if item["kind"] == "core" and not item["benchmark_runs"]
    ]
    return {
        "schema": "ctf-category-coverage-audit-v1",
        "root": str(root),
        "ok": not failing,
        "category_count": len(categories),
        "core_category_count": sum(1 for item in categories if item["kind"] == "core"),
        "specialty_category_count": sum(1 for item in categories if item["kind"] == "specialty"),
        "failing_count": len(failing),
        "failing_ids": [item["id"] for item in failing],
        "future_benchmark_needed": core_without_benchmark,
        "categories": categories,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit CTF category coverage across suite artifacts")
    parser.add_argument("--root", default=ROOT)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    result = audit_category_coverage(Path(args.root))
    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"category_coverage_ok={result['ok']}")
        print(f"future_benchmark_needed={result['future_benchmark_needed']}")
        for item in result["categories"]:
            status = "ok" if item["ok"] else "fail"
            print(f"{status}: {item['id']} topics={','.join(item['route_topics'])}")
            for problem in item["problems"]:
                print(f"  - {problem}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
