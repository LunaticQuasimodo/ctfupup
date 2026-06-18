#!/usr/bin/env python3
"""Extract high-signal lines from noisy CTF tool output."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


DEFAULT_PATTERNS = [
    r"flag\{[^}\n]{0,200}\}",
    r"ctf\{[^}\n]{0,200}\}",
    r"error|exception|warning|warn|traceback|segmentation fault|crash|core dumped",
    r"password|secret|token|key|admin|root",
    r"open\s+port|service|http|ssh|ftp|dns|smtp",
    r"canary|pie|nx|relro|libc|heap|stack",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize long CTF output")
    parser.add_argument("input")
    parser.add_argument("--max-lines", type=int, default=80)
    parser.add_argument("--pattern", action="append", default=[])
    args = parser.parse_args()

    text = Path(args.input).read_text(errors="replace", encoding="utf-8")
    patterns = [re.compile(p, re.I) for p in (args.pattern or DEFAULT_PATTERNS)]
    selected = []
    for idx, line in enumerate(text.splitlines(), start=1):
        if any(p.search(line) for p in patterns):
            selected.append(f"{idx}: {line[:500]}")
        if len(selected) >= args.max_lines:
            break
    if not selected:
        selected = [f"1: no default high-signal patterns matched; total_lines={len(text.splitlines())}"]
    print("\n".join(selected))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
