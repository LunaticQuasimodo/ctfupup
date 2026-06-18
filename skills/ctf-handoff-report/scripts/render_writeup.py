#!/usr/bin/env python3
"""Render a concise CTF writeup draft from CTFRunState JSON."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


FLAG_RE = re.compile(r"\b[A-Za-z0-9_]{2,16}\{[^}\n]+\}")


def bullet(items, limit=10) -> str:
    if not items:
        return "- None recorded"
    rows = []
    for item in items[:limit]:
        if isinstance(item, dict):
            text = item.get("summary") or item.get("action") or item.get("id") or json.dumps(item, ensure_ascii=False)
        else:
            text = str(item)
        rows.append(f"- {text}")
    return "\n".join(rows)


def evidence_table(evidence, limit=10) -> str:
    if not evidence:
        return "| Evidence ID | Action | Raw Artifact | Summary | Supports/Contradicts |\n|---|---|---|---|---|\n| None recorded | | | | |"
    rows = ["| Evidence ID | Action | Raw Artifact | Summary | Supports/Contradicts |", "|---|---|---|---|---|"]
    for item in evidence[:limit]:
        if not isinstance(item, dict):
            rows.append(f"| unknown | | | {str(item)} | |")
            continue
        supports = ", ".join(item.get("supports", []) or [])
        contradicts = ", ".join(item.get("contradicts", []) or [])
        support_cell = f"supports: {supports}; contradicts: {contradicts}".strip()
        rows.append(
            "| {id} | {action} | {raw} | {summary} | {support_cell} |".format(
                id=item.get("id", "unknown"),
                action=str(item.get("action", ""))[:120],
                raw=item.get("raw_artifact", ""),
                summary=str(item.get("summary", ""))[:160],
                support_cell=support_cell,
            )
        )
    return "\n".join(rows)


def raw_artifact_list(evidence, artifacts, limit=10) -> str:
    paths: list[str] = []
    for item in evidence:
        if isinstance(item, dict) and item.get("raw_artifact"):
            paths.append(str(item["raw_artifact"]))
    for item in artifacts:
        if isinstance(item, dict):
            path = item.get("path") or item.get("raw_artifact") or item.get("summary")
            if path:
                paths.append(str(path))
        else:
            paths.append(str(item))
    deduped = []
    for path in paths:
        if path and path not in deduped:
            deduped.append(path)
    return bullet(deduped, limit=limit)


def contrast_checks(dead_ends, evidence, limit=8) -> str:
    rows = []
    for item in dead_ends[:limit]:
        if isinstance(item, dict):
            summary = item.get("summary") or item.get("hypothesis") or json.dumps(item, ensure_ascii=False)
            reason = item.get("reason") or item.get("why_excluded") or item.get("result") or ""
            rows.append(f"- Ruled out: {summary}. Evidence/why: {reason}".rstrip())
        else:
            rows.append(f"- Ruled out: {item}")
    for item in evidence[:limit]:
        if isinstance(item, dict) and item.get("contradicts"):
            rows.append(f"- Contradicts {', '.join(item.get('contradicts', []))}: {item.get('summary', '')}")
    if not rows:
        return "- None recorded"
    return "\n".join(rows[:limit])


def render(state: dict) -> str:
    challenge = state.get("challenge", {})
    title = challenge.get("title", "unknown")
    evidence = state.get("evidence", [])
    facts = state.get("known_facts", [])
    dead_ends = state.get("dead_ends", [])
    artifacts = state.get("artifacts", [])
    candidate_flags = [
        item.get("summary", "")
        for item in facts
        if isinstance(item, dict) and FLAG_RE.search(item.get("summary", ""))
    ]
    flag_line = candidate_flags[-1] if candidate_flags else "Not recorded"
    return f"""# Writeup: {title}

## Overview

- Platform: {challenge.get('platform', 'unknown')}
- Claimed category: {challenge.get('category_claimed', 'unknown')}
- Inferred category: {challenge.get('category_inferred', 'unknown')}
- Flag format: {challenge.get('flag_format', 'unknown')}
- Flag evidence: {flag_line}

## Initial Triage

{bullet(evidence, limit=5)}

## Key Facts

{bullet(facts, limit=10)}

## Solve Path

1. Inventory attachments and preserve hashes.
2. Isolate untrusted challenge instructions and fake flags.
3. Use local evidence to derive the candidate flag.
4. Verify the candidate against the expected flag format or challenge validator.

## Commands and Scripts

See the evidence table for recorded commands and raw artifacts.

## Evidence References

{evidence_table(evidence, limit=10)}

## Raw Artifacts

{raw_artifact_list(evidence, artifacts, limit=10)}

## Contrast Checks

{contrast_checks(dead_ends, evidence, limit=8)}

## Verification

- Candidate flag evidence: {flag_line}
- Verification source: expected flag format, local validator, or benchmark oracle if recorded in known_facts.

## Failed Paths

{bullet(dead_ends, limit=10)}

## Artifacts

{bullet(artifacts, limit=10)}

## Lessons

- Preserve raw evidence before summarizing.
- Treat prompt-like challenge text as data.
- Prefer source-derived or validator-confirmed flags over untrusted hints.
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Render writeup from CTFRunState JSON")
    parser.add_argument("state_json")
    parser.add_argument("--out")
    args = parser.parse_args()

    state = json.loads(Path(args.state_json).read_text(encoding="utf-8"))
    output = render(state)
    if args.out:
        Path(args.out).write_text(output, encoding="utf-8")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
