#!/usr/bin/env python3
"""Audit deterministic skill trigger coverage and obvious routing conflicts."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCENARIO_DIR = ROOT / "forward-tests" / "scenarios"
TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9+#./_-]*", re.I)
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "before",
    "by",
    "ctf",
    "challenge",
    "do",
    "for",
    "from",
    "give",
    "goal",
    "has",
    "have",
    "how",
    "in",
    "inside",
    "into",
    "is",
    "it",
    "local",
    "may",
    "must",
    "need",
    "needs",
    "new",
    "not",
    "of",
    "or",
    "route",
    "should",
    "skills",
    "state",
    "task",
    "the",
    "this",
    "to",
    "triage",
    "use",
    "when",
    "with",
}
CUE_PATTERNS = {
    "ctf-master": [
        (r"\bnew\b.*\b(ctf|challenge|task)\b|\bfirst safe\b|\bfirst 10 minutes\b|\broute\b|\bctfrunstate\b|\bcheckpoint\b", 4, "master workflow phrase"),
    ],
    "ctf-web": [
        (r"\bflask\b|\brender_template_string\b|\bhttp\b|\brest\b|\bgraphql\b|\bapi\b|\blogin\b|\bcookie\b|\bsqli\b|\bssti\b|\bxss\b|\bupload\b", 5, "web/appsec cue"),
    ],
    "ctf-pwn-rev": [
        (r"\belf\b|\bchecksec\b|\blibc\b|\brop\b|\bgdb\b|\bpwndbg\b|\bnc\s+\w|\bstack canary\b|\bcrash offset\b|\bapk\b|\bjar\b|\bghidra\b", 5, "pwn/rev cue"),
    ],
    "ctf-forensics-crypto": [
        (r"\bpcap\b|\bmemory dump\b|\bdisk image\b|\bstego\b|\barchive\b|\blog\b|\bbase64\b|\brsa\b|\blattice\b|\boracle\b|\bcipher\b", 5, "forensics/crypto cue"),
    ],
    "ctf-specialty": [
        (r"\bllm\b|\brag\b|\btool abuse\b|\bcanary token\b|\bsmart contract\b|\bsolidity\b|\bevm\b|\bwallet\b|\brpc\b|\bfirmware\b|\biam\b|\bk8s\b|\bkubernetes\b", 5, "specialty cue"),
    ],
    "ctf-tool-preflight": [
        (r"\bpreflight\b|\bmissing\b|\bmissing_dependency\b|\bchecksec\b|\bgdb\b|\bpwndbg\b|\bida\b|\bghidra\b|\bdocker\b|\bvm\b|\bvpn\b|\bproxy\b|\blong output\b|\bcontext overload\b|\btool failures?\b", 5, "tool/preflight cue"),
    ],
    "ctf-knowledge": [
        (r"\bofficial docs\b|\bpapers?\b|\bctf wiki\b|\bhacktricks\b|\btool readme\b|\bsearch\b|\bsource evaluation\b|\bdistill\b|\bconvert\b.*\breferences?\b", 5, "knowledge cue"),
    ],
    "ctf-anti-injection": [
        (r"\bprompt injection\b|\bignore previous\b|\bfake flag\b|\bhidden prompt\b|\buntrusted\b|\bconversation history\b|\bwebhook\b|\btool poisoning\b", 5, "anti-injection cue"),
    ],
    "ctf-handoff-report": [
        (r"\bhandoff\b|\bwriteup\b|\breflection\b|\bdead ends?\b|\bstuck\b|\btakeover\b|\bnext solver\b", 5, "handoff/report cue"),
    ],
}


INLINE_PROBES = [
    {
        "id": "web-api-login",
        "title": "Web API login task",
        "prompt": "New CTF web task: Flask login app, cookies, REST API, SQLi and SSTI clues. Need first safe triage.",
        "expected_skills": ["ctf-master", "ctf-web"],
        "forbidden_top": ["ctf-pwn-rev", "ctf-specialty"],
    },
    {
        "id": "pwn-stack-canary-not-ai",
        "title": "Pwn stack canary is not AI canary",
        "prompt": "Pwn challenge with ELF ./chall, checksec shows stack canary, NX, libc.so.6, crash offset, and nc host 31337.",
        "expected_skills": ["ctf-master", "ctf-pwn-rev", "ctf-tool-preflight"],
        "forbidden_top": ["ctf-specialty"],
    },
    {
        "id": "knowledge-distillation",
        "title": "External knowledge distillation",
        "prompt": "Search official docs, papers, tool README, CTF Wiki and convert useful findings into compact ToolCards and references.",
        "expected_skills": ["ctf-knowledge", "ctf-tool-preflight"],
        "forbidden_top": ["ctf-handoff-report"],
    },
    {
        "id": "checkpoint-handoff",
        "title": "Checkpoint and handoff request",
        "prompt": "Create a checkpoint, handoff, writeup, and reflection from the current CTFRunState after three dead ends.",
        "expected_skills": ["ctf-master", "ctf-handoff-report"],
        "forbidden_top": ["ctf-web"],
    },
    {
        "id": "tool-health",
        "title": "Tool preflight request",
        "prompt": "Before running GDB, Docker, browser automation, proxy, VPN, IDA, and noisy scanners, check tool health and failures.",
        "expected_skills": ["ctf-tool-preflight"],
        "forbidden_top": ["ctf-knowledge"],
    },
]


def tokenize(text: str) -> set[str]:
    tokens = {item.lower().strip(".,:;()[]{}\"'") for item in TOKEN_RE.findall(text)}
    expanded = set(tokens)
    for token in tokens:
        expanded.update(part for part in re.split(r"[/_.-]+", token) if part)
    return {token for token in expanded if token and token not in STOPWORDS and len(token) > 1}


def parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        raise ValueError("missing YAML frontmatter")
    end = text.find("\n---\n", 4)
    if end == -1:
        raise ValueError("missing closing YAML frontmatter")
    data: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip().strip('"')
    return data


def load_skills(root: Path) -> dict[str, dict[str, Any]]:
    skills: dict[str, dict[str, Any]] = {}
    for skill_md in sorted((root / "skills").glob("ctf-*/SKILL.md")):
        text = skill_md.read_text(encoding="utf-8")
        fm = parse_frontmatter(text)
        name = fm.get("name", skill_md.parent.name)
        description = fm.get("description", "")
        skill_tokens = tokenize(f"{name} {description}")
        skills[name] = {
            "name": name,
            "path": str(skill_md.relative_to(root)),
            "description": description,
            "tokens": skill_tokens,
        }
    return skills


def load_forward_scenarios(scenario_dir: Path) -> list[dict[str, Any]]:
    scenarios = []
    for path in sorted(scenario_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        data["source"] = str(path)
        scenarios.append(data)
    return scenarios


def score_skill(prompt: str, skill: dict[str, Any]) -> dict[str, Any]:
    prompt_lc = prompt.lower()
    prompt_tokens = tokenize(prompt)
    skill_name = skill["name"]
    score = 0
    reasons: list[str] = []
    if f"${skill_name}" in prompt_lc or skill_name in prompt_lc:
        score += 100
        reasons.append("explicit skill mention")
    overlap = sorted(prompt_tokens & skill["tokens"])
    score += len(overlap)
    if overlap:
        reasons.append("token overlap: " + ", ".join(overlap[:8]))
    for pattern, weight, label in CUE_PATTERNS.get(skill_name, []):
        if re.search(pattern, prompt_lc):
            score += weight
            reasons.append(label)
    # Keep ctf-master visible for new challenge prompts, but do not swamp explicit support requests.
    if skill_name == "ctf-master" and re.search(r"\b(ctf|challenge|task|triage|route|state|checkpoint)\b", prompt_lc):
        score += 8
        reasons.append("master workflow cue")
    return {"skill": skill_name, "score": score, "reasons": reasons}


def rank_skills(prompt: str, skills: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    ranked = [score_skill(prompt, skill) for skill in skills.values()]
    ranked.sort(key=lambda item: (-item["score"], item["skill"]))
    return ranked


def evaluate_scenario(scenario: dict[str, Any], skills: dict[str, dict[str, Any]], *, top_margin: int) -> dict[str, Any]:
    expected = list(scenario.get("expected_skills", []))
    forbidden = list(scenario.get("forbidden_top", []))
    prompt = scenario.get("prompt", "")
    ranked = rank_skills(prompt, skills)
    top_n = max(len(expected) + top_margin, 3)
    top_ranked = ranked[:top_n]
    top_skills = [item["skill"] for item in top_ranked]
    top_scores = {item["skill"]: item["score"] for item in top_ranked}
    missing_expected = [skill for skill in expected if skill not in top_skills]
    forbidden_present = [skill for skill in forbidden if top_scores.get(skill, 0) > 0]
    unknown_expected = [skill for skill in expected if skill not in skills]
    return {
        "id": scenario.get("id"),
        "title": scenario.get("title", ""),
        "top_n": top_n,
        "expected_skills": expected,
        "forbidden_top": forbidden,
        "top_skills": top_skills,
        "ranked": ranked,
        "missing_expected": missing_expected,
        "forbidden_present": forbidden_present,
        "unknown_expected": unknown_expected,
        "ok": not missing_expected and not forbidden_present and not unknown_expected,
    }


def audit_triggers(root: Path, scenario_dir: Path, *, top_margin: int) -> dict[str, Any]:
    skills = load_skills(root)
    scenarios = load_forward_scenarios(scenario_dir) + INLINE_PROBES
    results = [evaluate_scenario(item, skills, top_margin=top_margin) for item in scenarios]
    weak_descriptions = [
        name for name, skill in sorted(skills.items())
        if len(skill["description"]) < 80 or "Use" not in skill["description"]
    ]
    failing = [item for item in results if not item["ok"]]
    ok = not failing and not weak_descriptions
    return {
        "schema": "ctf-skill-trigger-audit-v1",
        "root": str(root),
        "ok": ok,
        "skill_count": len(skills),
        "scenario_count": len(results),
        "failing_count": len(failing),
        "failing_ids": [item["id"] for item in failing],
        "weak_descriptions": weak_descriptions,
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit CTF skill trigger descriptions")
    parser.add_argument("--root", default=ROOT)
    parser.add_argument("--scenarios-dir", default=SCENARIO_DIR)
    parser.add_argument("--top-margin", type=int, default=2)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    result = audit_triggers(Path(args.root), Path(args.scenarios_dir), top_margin=args.top_margin)
    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"trigger_audit_ok={result['ok']}")
        for item in result["results"]:
            status = "ok" if item["ok"] else "fail"
            print(f"{status}: {item['id']} -> {', '.join(item['top_skills'])}")
            for missing in item["missing_expected"]:
                print(f"  missing expected: {missing}")
            for forbidden in item["forbidden_present"]:
                print(f"  forbidden in top: {forbidden}")
        for name in result["weak_descriptions"]:
            print(f"weak description: {name}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
