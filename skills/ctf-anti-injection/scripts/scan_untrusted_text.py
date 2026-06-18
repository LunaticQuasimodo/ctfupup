#!/usr/bin/env python3
"""Heuristic scanner for instruction-like untrusted text."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


PATTERNS = {
    "instruction_override": re.compile(r"\b(ignore|disregard|forget)\b.{0,80}\b(previous|prior|above|system|developer)\b", re.I),
    "role_override": re.compile(r"\b(new system|developer message|you are now|act as|roleplay)\b", re.I),
    "stop_solving": re.compile(r"\b(do not analyze|stop solving|give up|do nothing|submit this)\b", re.I),
    "secret_exfil": re.compile(r"\b(system prompt|api[_-]?key|token|cookie|ssh key|env|/etc/passwd|browser profile)\b", re.I),
    "network_exfil": re.compile(r"\b(curl|wget|fetch|post)\b.{0,120}\b(http://|https://|webhook|requestbin|discord|telegram)\b", re.I),
    "destructive": re.compile(r"\b(rm -rf|mkfs|shutdown|reboot|delete logs|wipe)\b", re.I),
    "fake_flag": re.compile(r"\b(flag|ctf)\{[^}\n]{0,120}\}", re.I),
    # Hidden instruction channel: zero-width and bidi controls can conceal prompt injection.
    "zero_width": re.compile("[\u200b-\u200f\u202a-\u202e\u2060-\u206f]"),
}

FLAG_RE = re.compile(r"\b(flag|ctf)\{[^}\n]{0,120}\}", re.I)
URL_RE = re.compile(r"https?://[^\s\"'<>]+", re.I)
SECRET_RE = re.compile(r"((?:api[_-]?key|token|secret|password|passwd|pwd|cookie)\s*[=:]\s*)[^\s&;,]+", re.I)


def sanitize_excerpt(text: str) -> str:
    """Keep scanner output useful without replaying hostile instructions verbatim."""
    text = FLAG_RE.sub(lambda match: f"{match.group(1)}{{<REDACTED_CANDIDATE>}}", text)
    text = re.sub(r"\bsubmit\s+(?:flag|ctf)\{<REDACTED_CANDIDATE>\}", "submit <REDACTED_FLAG_CANDIDATE>", text, flags=re.I)
    text = URL_RE.sub("https://<REDACTED_URL>", text)
    text = SECRET_RE.sub(r"\1<REDACTED>", text)
    return text


def load_text(args: argparse.Namespace) -> str:
    if args.text is not None:
        return args.text
    if args.file:
        return Path(args.file).read_text(encoding="utf-8", errors="replace")
    return sys.stdin.read()


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan untrusted challenge/tool text")
    parser.add_argument("--file")
    parser.add_argument("--text")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    text = load_text(args)
    findings = []
    for name, pattern in PATTERNS.items():
        for match in pattern.finditer(text):
            start = max(0, match.start() - 80)
            end = min(len(text), match.end() + 80)
            findings.append({
                "type": name,
                "span": [match.start(), match.end()],
                "excerpt": sanitize_excerpt(text[start:end].replace("\n", "\\n")[:300]),
            })
    severity = "hostile" if any(f["type"] in {"instruction_override", "secret_exfil", "network_exfil", "destructive"} for f in findings) else ("suspicious" if findings else "benign")
    result = {"severity": severity, "finding_count": len(findings), "findings": findings}
    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"severity={severity} findings={len(findings)}")
        for f in findings[:20]:
            print(f"- {f['type']}: {f['excerpt']}")
    return 1 if severity == "hostile" else 0


if __name__ == "__main__":
    raise SystemExit(main())
