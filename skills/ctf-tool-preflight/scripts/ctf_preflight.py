#!/usr/bin/env python3
"""CTF environment preflight checks."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from typing import Dict, List


PROFILES: Dict[str, List[str]] = {
    "general": ["python3", "git", "file", "strings", "sha256sum", "curl", "docker"],
    "web": ["curl", "jq", "ffuf", "feroxbuster", "nmap", "node", "python3"],
    "pwn-rev": ["file", "strings", "readelf", "objdump", "gdb", "python3", "checksec", "ROPgadget", "r2"],
    "forensics-crypto": ["file", "strings", "binwalk", "exiftool", "tshark", "zsteg", "python3", "sage"],
}


PROFILE_ALIASES = {
    "crypto": "forensics-crypto",
    "forensics": "forensics-crypto",
    "misc": "forensics-crypto",
    "pwn": "pwn-rev",
    "rev": "pwn-rev",
    "reverse": "pwn-rev",
}


VERSION_ARGS = {
    "python3": ["--version"],
    "docker": ["--version"],
    "curl": ["--version"],
    "git": ["--version"],
    "nmap": ["--version"],
    "gdb": ["--version"],
    "tshark": ["-v"],
    "sage": ["--version"],
    "strings": ["-"],
}


def version_of(tool: str) -> str:
    path = shutil.which(tool)
    if not path:
        return ""
    if tool == "strings":
        return "present"
    args = VERSION_ARGS.get(tool, ["--version"])
    try:
        out = subprocess.run([path, *args], check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=5)
        return (out.stdout or "").splitlines()[0][:200] if out.stdout else "present"
    except Exception as exc:  # pragma: no cover - defensive for local env differences
        return f"present but version failed: {exc}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Check common CTF tools")
    parser.add_argument("--profile", choices=sorted(set(PROFILES) | set(PROFILE_ALIASES)), default="general")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()
    profile = PROFILE_ALIASES.get(args.profile, args.profile)

    checks = []
    for tool in PROFILES[profile]:
        path = shutil.which(tool)
        checks.append({
            "tool": tool,
            "present": bool(path),
            "path": path or "",
            "version": version_of(tool) if path else "",
        })
    result = {
        "requested_profile": args.profile,
        "profile": profile,
        "ok": all(item["present"] for item in checks),
        "checks": checks,
        "missing": [item["tool"] for item in checks if not item["present"]],
    }
    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        for item in checks:
            status = "OK" if item["present"] else "MISSING"
            print(f"{status:7} {item['tool']:16} {item['version']}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
