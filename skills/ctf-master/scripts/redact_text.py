#!/usr/bin/env python3
"""Redact common secrets from CTF notes and tool output."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


PATTERNS = [
    (re.compile(r"(Authorization:\s*Bearer\s+)[A-Za-z0-9._~+/=-]+", re.I), r"\1<REDACTED>"),
    (re.compile(r"((?:api[_-]?key|token|secret|password|passwd|pwd)\s*[=:]\s*)[^\s&;,]+", re.I), r"\1<REDACTED>"),
    (re.compile(r"((?:sessionid|sid|sid_tt|cookie)\s*[=:]\s*)[^\s;]+", re.I), r"\1<REDACTED>"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S), "<REDACTED_PRIVATE_KEY>"),
    (re.compile(r"\b[A-Za-z0-9+/]{32,}={0,2}\b"), "<REDACTED_LONG_TOKEN>"),
]


def redact(text: str) -> str:
    for pattern, replacement in PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def main() -> int:
    parser = argparse.ArgumentParser(description="Redact common secrets")
    parser.add_argument("--file")
    parser.add_argument("--out")
    args = parser.parse_args()

    text = Path(args.file).read_text(encoding="utf-8", errors="replace") if args.file else sys.stdin.read()
    output = redact(text)
    if args.out:
        Path(args.out).write_text(output, encoding="utf-8")
    else:
        sys.stdout.write(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
