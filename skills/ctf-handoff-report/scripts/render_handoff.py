#!/usr/bin/env python3
"""Render a CTFRunState JSON file into a Markdown handoff draft."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def lines(items, limit=10):
    if not items:
        return "- None recorded"
    out = []
    for item in items[:limit]:
        if isinstance(item, dict):
            label = item.get("summary") or item.get("action") or item.get("id") or json.dumps(item, ensure_ascii=False)
        else:
            label = str(item)
        out.append(f"- {label}")
    return "\n".join(out)


def render(state: dict) -> str:
    challenge = state.get("challenge", {})
    parts = [
        f"# Handoff: {challenge.get('title', 'unknown')}",
        "",
        "## Challenge",
        f"- Platform: {challenge.get('platform', 'unknown')}",
        f"- Claimed category: {challenge.get('category_claimed', 'unknown')}",
        f"- Inferred category: {challenge.get('category_inferred', 'unknown')}",
        f"- Flag format: {challenge.get('flag_format', 'unknown')}",
        f"- Scope status: {challenge.get('scope_status', 'unknown')}",
        "",
        "## Known Facts",
        lines(state.get("known_facts", [])),
        "",
        "## Evidence",
        lines(state.get("evidence", []), limit=20),
        "",
        "## Hypotheses",
        lines(state.get("hypotheses", [])),
        "",
        "## Attempts",
        lines(state.get("attempts", []), limit=20),
        "",
        "## Dead Ends",
        lines(state.get("dead_ends", []), limit=20),
        "",
        "## Next Actions",
        lines(state.get("next_actions", []), limit=5),
        "",
        "## Artifacts",
        lines(state.get("artifacts", []), limit=20),
    ]
    return "\n".join(parts) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Render handoff from CTFRunState JSON")
    parser.add_argument("state_json")
    parser.add_argument("--out")
    args = parser.parse_args()

    state = json.loads(Path(args.state_json).read_text(encoding="utf-8"))
    output = render(state)
    if args.out:
        Path(args.out).write_text(output, encoding="utf-8")
    else:
        print(output, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
