#!/usr/bin/env python3
"""Build a safe attachment inventory for CTF artifacts."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import mimetypes
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any


SUSPICIOUS = [
    re.compile(r"\b(ignore|disregard|forget)\b.{0,80}\b(previous|system|developer|instructions)\b", re.I),
    re.compile(r"\b(submit this|do not analyze|stop solving|send .*token|curl https?://)\b", re.I),
    re.compile("[\u200b-\u200f\u202a-\u202e\u2060-\u206f]"),
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def file_type(path: Path) -> str:
    file_bin = shutil.which("file")
    if file_bin:
        proc = subprocess.run([file_bin, "-b", str(path)], text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        if proc.stdout.strip():
            return proc.stdout.strip()
    return mimetypes.guess_type(path.name)[0] or "unknown"


def suspicious_count(path: Path, max_bytes: int = 200_000) -> int:
    try:
        data = path.read_bytes()[:max_bytes]
    except OSError:
        return 0
    text = data.decode("utf-8", errors="ignore")
    return sum(1 for pattern in SUSPICIOUS for _ in pattern.finditer(text))


def iter_files(paths: list[Path], recursive: bool) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if path.is_file():
            files.append(path)
        elif path.is_dir() and recursive:
            files.extend(p for p in path.rglob("*") if p.is_file())
        elif path.is_dir():
            files.extend(p for p in path.iterdir() if p.is_file())
    return sorted(files)


def record_for(path: Path) -> dict[str, Any]:
    suspicion = suspicious_count(path)
    return {
        "path": str(path),
        "size": path.stat().st_size,
        "sha256": sha256(path),
        "type": file_type(path),
        "trust_label": "untrusted_challenge",
        "suspicious_instruction_count": suspicion,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Inventory CTF attachments")
    parser.add_argument("paths", nargs="+")
    parser.add_argument("--recursive", action="store_true")
    parser.add_argument("--state", help="Optional CTFRunState JSON to update challenge.attachments")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    files = iter_files([Path(p) for p in args.paths], args.recursive)
    records = [record_for(path) for path in files]
    result = {"generated_at": dt.datetime.now(dt.timezone.utc).isoformat(), "attachments": records}

    if args.state:
        state_path = Path(args.state)
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state.setdefault("challenge", {}).setdefault("attachments", [])
        existing = {item.get("path") for item in state["challenge"]["attachments"] if isinstance(item, dict)}
        for item in records:
            if item["path"] not in existing:
                state["challenge"]["attachments"].append(item)
        state["updated_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
        state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        for item in records:
            marker = " suspicious" if item["suspicious_instruction_count"] else ""
            print(f"{item['sha256']}  {item['size']:>8}  {item['type']}  {item['path']}{marker}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
