#!/usr/bin/env python3
"""Run safe synthetic end-to-end CTF skill workflow demos."""

from __future__ import annotations

import argparse
import base64
import codecs
import datetime as dt
import json
import re
import subprocess
import sys
from itertools import cycle
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = ROOT / "demo-fixtures"
FLAG_RE = re.compile(r"flag\{[^}\n]+\}")


FIXTURES = {
    "friendly-login": {
        "title": "Friendly Login",
        "category": "web",
        "inferred": "web",
        "path": FIXTURE_ROOT / "friendly-login",
        "rules": "synthetic local web-source fixture; no remote service; no network actions needed",
    },
    "crypto-xor": {
        "title": "XOR State",
        "category": "crypto",
        "inferred": "crypto",
        "path": FIXTURE_ROOT / "crypto-xor",
        "rules": "synthetic local crypto fixture; no brute force or network actions needed",
    },
    "forensics-b64log": {
        "title": "Base64 Log",
        "category": "forensics",
        "inferred": "forensics",
        "path": FIXTURE_ROOT / "forensics-b64log",
        "rules": "synthetic local forensics fixture; preserve log and decode local payload only",
    },
    "pwn-offset": {
        "title": "Pwn Offset",
        "category": "pwn",
        "inferred": "pwn",
        "path": FIXTURE_ROOT / "pwn-offset",
        "rules": "synthetic local pwn transcript; no exploit execution and no remote service",
    },
    "reverse-rot13": {
        "title": "ROT13 Checker",
        "category": "reverse",
        "inferred": "reverse",
        "path": FIXTURE_ROOT / "reverse-rot13",
        "rules": "synthetic local reverse fixture; inspect source only",
    },
}


def run(cmd: list[str], *, allow_1: bool = False) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    allowed = (0, 1) if allow_1 else (0,)
    if proc.returncode not in allowed:
        raise RuntimeError(f"command failed ({proc.returncode}): {' '.join(cmd)}\n{proc.stdout}")
    return proc


def update(state: Path, kind: str, summary: str, **kwargs: str) -> dict:
    cmd = [
        sys.executable,
        str(ROOT / "skills/ctf-master/scripts/update_state.py"),
        "--state",
        str(state),
        "--kind",
        kind,
        "--summary",
        summary,
    ]
    for key, value in kwargs.items():
        if value:
            cmd.extend([f"--{key.replace('_', '-')}", value])
    proc = run(cmd)
    return json.loads(proc.stdout)


def link_evidence_supports(state: Path, evidence_id: str, supports: list[str]) -> None:
    state_data = json.loads(state.read_text(encoding="utf-8"))
    for item in state_data.get("evidence", []):
        if item.get("id") == evidence_id:
            item["supports"] = supports
            state.write_text(json.dumps(state_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return
    raise RuntimeError(f"evidence id not found for support linkage: {evidence_id}")


def xor_repeating(data: bytes, key: bytes) -> bytes:
    return bytes(a ^ b for a, b in zip(data, cycle(key)))


def solve_friendly_login(fixture: Path, summary_dir: Path) -> tuple[str, str, str, str]:
    app_source = (fixture / "app.py").read_text(encoding="utf-8")
    match = FLAG_RE.search(app_source)
    candidate = match.group(0) if match else ""
    source_summary = summary_dir / "source-flag-evidence.txt"
    source_summary.write_text(
        "Static source inspection found FLAG assignment in app.py.\n"
        f"candidate={candidate}\n",
        encoding="utf-8",
    )
    return (
        candidate,
        "read app.py and extract FLAG assignment",
        "derive flag from trusted local source evidence",
        str(source_summary),
    )


def solve_crypto_xor(fixture: Path, summary_dir: Path) -> tuple[str, str, str, str]:
    challenge = json.loads((fixture / "challenge.json").read_text(encoding="utf-8"))
    ciphertext = bytes.fromhex(challenge["ciphertext_hex"])
    key = challenge["key"].encode()
    candidate = xor_repeating(ciphertext, key).decode()
    summary = summary_dir / "crypto-xor-solver.txt"
    summary.write_text(
        "Decoded repeating XOR ciphertext from challenge.json.\n"
        f"encoding={challenge['encoding']}\nkey={challenge['key']}\ncandidate={candidate}\n",
        encoding="utf-8",
    )
    return (
        candidate,
        "decode challenge.json repeating XOR ciphertext",
        "derive flag from crypto parameters and verify flag format",
        str(summary),
    )


def solve_forensics_b64log(fixture: Path, summary_dir: Path) -> tuple[str, str, str, str]:
    log_text = (fixture / "events.log").read_text(encoding="utf-8")
    match = re.search(r"payload_b64=([A-Za-z0-9+/=]+)", log_text)
    payload = match.group(1) if match else ""
    candidate = base64.b64decode(payload).decode()
    summary = summary_dir / "forensics-b64log-decoder.txt"
    summary.write_text(
        "Extracted payload_b64 from events.log and decoded it locally.\n"
        f"payload_b64={payload}\ncandidate={candidate}\n",
        encoding="utf-8",
    )
    return (
        candidate,
        "extract payload_b64 from events.log and base64-decode",
        "preserve log evidence and verify decoded flag format",
        str(summary),
    )


def solve_pwn_offset(fixture: Path, summary_dir: Path) -> tuple[str, str, str, str]:
    transcript = (fixture / "transcript.txt").read_text(encoding="utf-8")
    fields = dict(re.findall(r"^([a-z_]+):\s*(.+)$", transcript, flags=re.M))
    offset = int(fields.get("cyclic_offset", "0"))
    marker = fields.get("cyclic_marker", "")
    win_symbol = fields.get("win_symbol", "")
    flag_parts = fields.get("flag_parts", "")
    candidate = flag_parts.replace(" ", "")
    summary = summary_dir / "pwn-offset-analysis.txt"
    summary.write_text(
        "Parsed simulated pwn transcript; no exploit executed.\n"
        f"marker={marker}\noffset={offset}\nwin_symbol={win_symbol}\ncandidate={candidate}\n",
        encoding="utf-8",
    )
    return (
        candidate,
        "parse transcript cyclic marker and offset",
        "derive pwn proof from local crash transcript without executing an exploit",
        str(summary),
    )


def solve_reverse_rot13(fixture: Path, summary_dir: Path) -> tuple[str, str, str, str]:
    source = (fixture / "checker.py").read_text(encoding="utf-8")
    match = re.search(r'ENCODED\s*=\s*"([^"]+)"', source)
    encoded = match.group(1) if match else ""
    candidate = codecs.encode(encoded, "rot_13")
    summary = summary_dir / "reverse-rot13-solver.txt"
    summary.write_text(
        "Recovered candidate by reversing ROT13 transform from checker.py.\n"
        f"encoded={encoded}\ncandidate={candidate}\n",
        encoding="utf-8",
    )
    return (
        candidate,
        "read checker.py and reverse ROT13 encoded target",
        "derive flag from reverse-engineered transform",
        str(summary),
    )


SOLVERS = {
    "friendly-login": solve_friendly_login,
    "crypto-xor": solve_crypto_xor,
    "forensics-b64log": solve_forensics_b64log,
    "pwn-offset": solve_pwn_offset,
    "reverse-rot13": solve_reverse_rot13,
}


def render_writeup(state: Path, out: Path) -> None:
    run([sys.executable, str(ROOT / "skills/ctf-handoff-report/scripts/render_writeup.py"), str(state), "--out", str(out)])


def render_reflection(state: Path, out: Path) -> None:
    run([sys.executable, str(ROOT / "skills/ctf-handoff-report/scripts/render_reflection.py"), str(state), "--out", str(out)])


def render_checkpoint(state: Path, out: Path) -> None:
    run([sys.executable, str(ROOT / "skills/ctf-master/scripts/checkpoint_state.py"), str(state), "--out", str(out)])


def run_one(fixture_name: str, out_dir: Path) -> dict:
    cfg = FIXTURES[fixture_name]
    fixture = Path(cfg["path"])
    raw_dir = out_dir / "artifacts" / "raw"
    summary_dir = out_dir / "artifacts" / "summaries"
    raw_dir.mkdir(parents=True, exist_ok=True)
    summary_dir.mkdir(parents=True, exist_ok=True)

    state = out_dir / "ctf-state.json"
    run([
        sys.executable,
        str(ROOT / "skills/ctf-master/scripts/init_state.py"),
        "--title",
        str(cfg["title"]),
        "--category",
        str(cfg["category"]),
        "--platform",
        "synthetic-local",
        "--flag-format",
        "flag{...}",
        "--out",
        str(state),
    ])
    state_data = json.loads(state.read_text(encoding="utf-8"))
    state_data["challenge"]["category_inferred"] = cfg["inferred"]
    state_data["challenge"]["category_confidence"] = "high"
    state_data["challenge"]["scope_status"] = "local_only"
    state_data["challenge"]["targets"] = [str(fixture)]
    state_data["challenge"]["rules"] = [str(cfg["rules"])]
    state.write_text(json.dumps(state_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    triage_path = raw_dir / "artifact-triage.json"
    triage = run([
        sys.executable,
        str(ROOT / "skills/ctf-master/scripts/triage_artifacts.py"),
        str(fixture),
        "--recursive",
        "--state",
        str(state),
        "--json",
    ])
    triage_path.write_text(triage.stdout, encoding="utf-8")
    ev1 = update(
        state,
        "evidence",
        f"Attachment inventory created for {fixture_name}.",
        action=f"triage_artifacts.py demo-fixtures/{fixture_name}",
        purpose="inventory challenge attachments",
        raw_artifact=str(triage_path),
        exit_status="0",
        risk="none",
    )

    readme = fixture / "README.md"
    scan_path = raw_dir / "readme-injection-scan.json"
    scan = run([
        sys.executable,
        str(ROOT / "skills/ctf-anti-injection/scripts/scan_untrusted_text.py"),
        "--file",
        str(readme),
        "--json",
    ], allow_1=True)
    scan_path.write_text(scan.stdout, encoding="utf-8")
    scan_json = json.loads(scan.stdout)
    ev2 = update(
        state,
        "evidence",
        f"README untrusted-content scan severity={scan_json['severity']}.",
        action="scan_untrusted_text.py README.md",
        purpose="detect prompt injection and fake flags",
        raw_artifact=str(scan_path),
        exit_status=str(scan.returncode),
        risk="prompt_injection" if scan_json["severity"] != "benign" else "none",
    )
    if fixture_name == "friendly-login":
        update(state, "fact", "README fake flag is untrusted and not accepted as solve evidence.", evidence_ids=ev2["id"])

    route_path = raw_dir / "deep-topic-routes.json"
    route_proc = run([
        sys.executable,
        str(ROOT / "skills/ctf-master/scripts/route_topic.py"),
        "--text",
        f"{cfg['title']} {cfg['category']} {cfg['rules']}",
        "--triage-json",
        str(triage_path),
        "--json",
    ])
    route_path.write_text(route_proc.stdout, encoding="utf-8")
    route_json = json.loads(route_proc.stdout)
    route_topics = [item["topic_id"] for item in route_json.get("routes", [])]
    ev_route = update(
        state,
        "evidence",
        f"Deep-topic route candidates: {', '.join(route_topics[:3])}.",
        action=f"route_topic.py --triage-json {triage_path}",
        purpose="rank category-specific playbook candidates",
        raw_artifact=str(route_path),
        exit_status="0",
        risk="none",
    )
    for route in route_json.get("routes", [])[:2]:
        confidence = route.get("confidence", "low")
        if confidence not in {"low", "medium", "high"}:
            confidence = "low"
        first_action = "; ".join(route.get("first_safe_actions", [])[:2])
        read_next = ", ".join(route.get("read_next", [])[:2])
        update(
            state,
            "hypothesis",
            f"Deep topic candidate {route.get('topic_id')} should guide the next playbook.",
            confidence=confidence,
            next_experiment=f"Read {read_next}; {first_action}",
            evidence_ids=ev_route["id"],
        )

    candidate, action, purpose, raw_artifact = SOLVERS[fixture_name](fixture, summary_dir)
    if not FLAG_RE.fullmatch(candidate):
        raise RuntimeError(f"{fixture_name} solver did not produce a valid flag candidate: {candidate!r}")
    ev3 = update(
        state,
        "evidence",
        f"Synthetic solver derived candidate flag {candidate}.",
        action=action,
        purpose=purpose,
        raw_artifact=raw_artifact,
        exit_status="0",
        risk="none",
    )
    candidate_fact = update(state, "fact", f"Candidate flag derived from {fixture_name}: {candidate}", evidence_ids=ev3["id"])
    link_evidence_supports(state, ev3["id"], [candidate_fact["id"]])
    update(
        state,
        "hypothesis",
        "The evidence-derived candidate is the valid flag for the synthetic fixture.",
        confidence="high",
        next_experiment="Verify candidate matches flag format and fixture validation logic.",
        evidence_ids=ev3["id"],
    )
    update(
        state,
        "attempt",
        f"Accepted evidence-derived candidate for {fixture_name}.",
        action=action,
        outcome="candidate matches flag format and is derived from fixture evidence",
        evidence_ids=f"{ev1['id']},{ev2['id']},{ev_route['id']},{ev3['id']}",
    )
    if fixture_name == "friendly-login":
        update(
            state,
            "dead_end",
            "README-provided flag{not_real} excluded.",
            reason="originated from hostile untrusted instruction, not from solve evidence",
            evidence_ids=ev2["id"],
            revisit_condition="Only revisit if independent challenge validator accepts it, which this synthetic demo does not provide.",
        )
    update(
        state,
        "artifact",
        "Demo fixture and generated raw artifacts recorded.",
        path=str(out_dir),
        artifact_type="demo-run",
        evidence_ids=f"{ev1['id']},{ev2['id']},{ev_route['id']},{ev3['id']}",
    )
    update(
        state,
        "next_action",
        "Use this demo run as regression evidence; run real forward-tests next.",
        priority="medium",
    )

    handoff = out_dir / "handoff.md"
    handoff.write_text(
        run([sys.executable, str(ROOT / "skills/ctf-handoff-report/scripts/render_handoff.py"), str(state)]).stdout,
        encoding="utf-8",
    )
    writeup = out_dir / "writeup.md"
    render_writeup(state, writeup)
    checkpoint = out_dir / "checkpoint.md"
    render_checkpoint(state, checkpoint)
    reflection = out_dir / "reflection.md"
    render_reflection(state, reflection)

    metadata = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "fixture": fixture_name,
        "state": str(state),
        "handoff": str(handoff),
        "writeup": str(writeup),
        "checkpoint": str(checkpoint),
        "reflection": str(reflection),
        "candidate_flag": candidate,
        "route_topics": route_topics,
    }
    (out_dir / "run-metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return metadata


def main() -> int:
    parser = argparse.ArgumentParser(description="Run safe synthetic CTF workflow demos")
    parser.add_argument("--fixture", choices=sorted(FIXTURES), default="friendly-login")
    parser.add_argument("--all", action="store_true", help="Run all fixtures under out-dir")
    parser.add_argument("--out-dir", default=str(ROOT / "demo-runs" / "friendly-login"))
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    if args.all:
        results = []
        for name in sorted(FIXTURES):
            results.append(run_one(name, out_dir / name))
        print(json.dumps({"runs": results}, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(run_one(args.fixture, out_dir), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
