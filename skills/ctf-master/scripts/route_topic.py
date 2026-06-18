#!/usr/bin/env python3
"""Rank CTF deep-topic routes from challenge text and triage metadata."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any


MAX_FILE_BYTES = 200_000


TOPICS: list[dict[str, Any]] = [
    {
        "topic_id": "web.ssti",
        "category": "web",
        "skill": "ctf-web",
        "read_next": ["skills/ctf-web/references/web-triage.md"],
        "signals": [
            (r"\brender_template_string\b|\bjinja2?\b|\btwig\b|\bejs\b|\bpug\b|\bhandlebars\b", 3, "template engine"),
            (r"\{\{[^}\n]{0,80}\}\}|\{%[^%\n]{0,80}%\}", 3, "template syntax"),
            (r"\bssti\b|\bserver[- ]side template\b", 3, "ssti label"),
        ],
        "first_safe_actions": ["map route to render sink", "save baseline and one bounded template probe"],
        "evidence_gates": ["controlled input reaches template sink", "baseline/probe response comparison saved"],
    },
    {
        "topic_id": "web.sql-injection",
        "category": "web",
        "skill": "ctf-web",
        "read_next": ["skills/ctf-web/references/web-triage.md"],
        "signals": [
            (r"\bsqlite\b|\bmysql\b|\bpostgres(?:ql)?\b|\bselect\b.+\bfrom\b|\bunion\b.+\bselect\b", 2, "sql terms"),
            (r"\braw\s+query\b|\bexecute\(|\bwhere\b.+\bf-string\b|\bstring concatenation\b", 2, "raw query construction"),
            (r"\bsqli\b|\bsql injection\b|\blogin bypass\b", 3, "sqli label"),
        ],
        "first_safe_actions": ["save normal request", "test one differential input"],
        "evidence_gates": ["differential response is attributable to SQL path"],
    },
    {
        "topic_id": "web.ssrf",
        "category": "web",
        "skill": "ctf-web",
        "read_next": ["skills/ctf-web/references/web-triage.md"],
        "signals": [
            (r"\bssrf\b|\bwebhook\b|\bfetch url\b|\burlfetch\b|\bimage proxy\b", 3, "url fetch feature"),
            (r"169\.254\.169\.254|\bmetadata service\b|\binternal url\b", 3, "metadata clue"),
        ],
        "first_safe_actions": ["identify URL sink", "use in-scope local/canary endpoint only"],
        "evidence_gates": ["outbound request proof stays in challenge scope"],
    },
    {
        "topic_id": "web.file-upload",
        "category": "web",
        "skill": "ctf-web",
        "read_next": ["skills/ctf-web/references/web-triage.md"],
        "signals": [
            (r"\bupload\b|\bmultipart/form-data\b|\bwerkzeug\.FileStorage\b", 2, "upload flow"),
            (r"\bzip\b|\btar\b|\bextractall\b|\bimagemagick\b|\bconvert\b|\bpdf\b", 2, "file transform"),
            (r"\bpath traversal\b|\b\.\./\b|\bsecure_filename\b", 2, "path handling"),
        ],
        "first_safe_actions": ["map accepted file types", "find storage and transform path"],
        "evidence_gates": ["file write/read path proven without destructive payload"],
    },
    {
        "topic_id": "web.jwt-session",
        "category": "web",
        "skill": "ctf-web",
        "read_next": ["skills/ctf-web/references/web-triage.md"],
        "signals": [
            (r"\bjwt\b|\bjson web token\b|\bauthorization:\s*bearer\b", 3, "jwt token"),
            (r"\balg\b|\bkid\b|\bhs256\b|\brs256\b|\bsecret_key\b|\bsession cookie\b", 2, "token verification clue"),
        ],
        "first_safe_actions": ["decode token without modifying", "inspect verification key path"],
        "evidence_gates": ["signature behavior or key source is proven"],
    },
    {
        "topic_id": "pwn.stack",
        "category": "pwn",
        "skill": "ctf-pwn-rev",
        "read_next": ["skills/ctf-pwn-rev/references/pwn-rev-triage.md"],
        "signals": [
            (r"\bELF\b|\bchecksec\b|\bNX\b|\bPIE\b|\bcanary\b", 2, "binary protections"),
            (r"\bret2win\b|\bROP\b|\bcyclic\b|\bRIP\b|\bEIP\b|\boverflow\b", 3, "stack control"),
            (r"\bgets\(|\bstrcpy\(|\bsprintf\(|\bread\(0", 2, "unsafe input"),
        ],
        "first_safe_actions": ["save file/checksec/readelf output", "reproduce local crash"],
        "evidence_gates": ["offset/control proof exists before exploit claim"],
    },
    {
        "topic_id": "pwn.heap",
        "category": "pwn",
        "skill": "ctf-pwn-rev",
        "read_next": ["skills/ctf-pwn-rev/references/pwn-rev-triage.md"],
        "signals": [
            (r"\bmalloc\b|\bfree\b|\btcache\b|\bfastbin\b|\bunsorted bin\b", 3, "heap allocator"),
            (r"\buse-after-free\b|\bUAF\b|\bdouble free\b|\bheap overflow\b", 3, "heap bug label"),
        ],
        "first_safe_actions": ["map menu protocol", "record allocator state around primitive"],
        "evidence_gates": ["heap primitive is shown before target overwrite"],
    },
    {
        "topic_id": "rev.checker",
        "category": "reverse",
        "skill": "ctf-pwn-rev",
        "read_next": ["skills/ctf-pwn-rev/references/pwn-rev-triage.md"],
        "signals": [
            (r"\bcheck(?:er)?\b|\blicense\b|\bkeygen\b|\bserial\b|\bsuccess\b|\bfailure\b", 2, "checker wording"),
            (r"\bstrcmp\b|\bmemcmp\b|\brot13\b|\bbase64_decode\b|\bcustom check\b", 2, "comparison or encoding"),
            (r"\bapk\b|\bsmali\b|\bjadx\b|\bghidra\b|\bida\b", 1, "reverse tooling"),
        ],
        "first_safe_actions": ["locate input-to-decision path", "verify recovered value against checker"],
        "evidence_gates": ["binary/source accepts candidate"],
    },
    {
        "topic_id": "rev.vm-obfuscation",
        "category": "reverse",
        "skill": "ctf-pwn-rev",
        "read_next": ["skills/ctf-pwn-rev/references/pwn-rev-triage.md"],
        "signals": [
            (r"\bbytecode\b|\bopcode\b|\bdispatch(?:er)?\b|\bvm\b|\bvirtual machine\b", 3, "vm terms"),
            (r"\bflatten(?:ed)?\b|\bobfuscat(?:ed|ion)\b|\bpacked\b", 2, "obfuscation terms"),
        ],
        "first_safe_actions": ["map opcode format", "trace one instruction path"],
        "evidence_gates": ["decoded instruction semantics are backed by trace"],
    },
    {
        "topic_id": "crypto.rsa",
        "category": "crypto",
        "skill": "ctf-forensics-crypto",
        "read_next": ["skills/ctf-forensics-crypto/references/crypto-triage.md"],
        "signals": [
            (r"\bRSA\b|\bmodulus\b|\bpublic exponent\b|\bprivate exponent\b|\bPEM\b", 3, "rsa label"),
            (r"\bn\s*=|\be\s*=|\bc\s*=|\bp\s*=|\bq\s*=|-----BEGIN (?:RSA )?(?:PUBLIC|PRIVATE) KEY-----", 2, "rsa parameters"),
            (r"\be\s*=\s*3\b|\bcommon modulus\b|\bshared prime\b|\bcoppersmith\b|\bfermat\b", 3, "rsa weakness"),
        ],
        "first_safe_actions": ["list parameters", "state exact attack condition"],
        "evidence_gates": ["decryption/re-encryption or validator proof"],
    },
    {
        "topic_id": "crypto.xor-stream",
        "category": "crypto",
        "skill": "ctf-forensics-crypto",
        "read_next": ["skills/ctf-forensics-crypto/references/crypto-triage.md"],
        "signals": [
            (r"\bxor\b|\brepeating[- ]key\b|\bstream cipher\b|\bkeystream\b", 3, "xor or stream"),
            (r"\bnonce reuse\b|\bCTR\b|\bGCM\b|\bknown plaintext\b|\bcrib\b", 3, "reuse or crib"),
            (r"\bciphertext_hex\b|\bhex ciphertext\b", 2, "ciphertext format"),
        ],
        "first_safe_actions": ["identify key/reuse/crib evidence", "decode one sample and verify format"],
        "evidence_gates": ["keystream or key derivation is saved"],
    },
    {
        "topic_id": "crypto.prng",
        "category": "crypto",
        "skill": "ctf-forensics-crypto",
        "read_next": ["skills/ctf-forensics-crypto/references/crypto-triage.md"],
        "signals": [
            (r"\bMT19937\b|\bmersenne\b|\brandom\.seed\b|\bPRNG\b|\btimestamp seed\b", 3, "prng clue"),
            (r"\brandint\b|\brandrange\b|\brandom outputs\b|\bstate recovery\b", 2, "random outputs"),
        ],
        "first_safe_actions": ["record outputs and generator", "prove seed/state bound"],
        "evidence_gates": ["predicted output validates against sample"],
    },
    {
        "topic_id": "forensics.pcap",
        "category": "forensics",
        "skill": "ctf-forensics-crypto",
        "read_next": ["skills/ctf-forensics-crypto/references/forensics-triage.md"],
        "signals": [
            (r"\bpcapng?\b|\bwireshark\b|\btshark\b|\btcpdump\b", 3, "packet capture"),
            (r"\bHTTP object\b|\bDNS\b|\bUSB\b|\b802\.11\b|\bWPA\b|\bTLS key log\b", 2, "protocol clue"),
        ],
        "first_safe_actions": ["hash capture", "inventory protocols and conversations"],
        "evidence_gates": ["extracted objects have raw paths and source packet context"],
    },
    {
        "topic_id": "forensics.stego",
        "category": "forensics",
        "skill": "ctf-forensics-crypto",
        "read_next": ["skills/ctf-forensics-crypto/references/forensics-triage.md"],
        "signals": [
            (r"\bstego\b|\bLSB\b|\bzsteg\b|\bstegsolve\b|\boutguess\b", 3, "stego label"),
            (r"\bexif\b|\bmetadata\b|\bpng\b|\bjpg\b|\bjpeg\b|\baudio\b|\bwav\b|\bmp3\b", 1, "media metadata"),
        ],
        "first_safe_actions": ["hash source media", "run metadata and format checks first"],
        "evidence_gates": ["extracted artifact path and transform command saved"],
    },
    {
        "topic_id": "forensics.archive",
        "category": "forensics",
        "skill": "ctf-forensics-crypto",
        "read_next": ["skills/ctf-forensics-crypto/references/forensics-triage.md"],
        "signals": [
            (r"\bzip\b|\brar\b|\b7z\b|\btar\b|\bgzip\b|\bbzip2\b|\bxz\b", 2, "archive type"),
            (r"\bpassword protected\b|\bcrc\b|\bcorrupt(?:ed)?\b|\bfile carving\b|\bbinwalk\b", 2, "archive/carving clue"),
        ],
        "first_safe_actions": ["list archive safely", "preserve hashes before extraction"],
        "evidence_gates": ["extracted path and password/source proof saved"],
    },
    {
        "topic_id": "forensics.log-encoding",
        "category": "forensics",
        "skill": "ctf-forensics-crypto",
        "read_next": ["skills/ctf-forensics-crypto/references/forensics-triage.md"],
        "signals": [
            (r"\blog(?:s|file)?\b|\bevents?\.log\b|\btimestamp\b|\bsource=", 2, "log artifact"),
            (r"\bbase64\b|\bb64\b|\bpayload_b64\b|\bdecode\b|\bencoded payload\b", 3, "encoded log payload"),
            (r"\bgrep\b|\bawk\b|\btimeline\b|\bextract .*field\b", 1, "log workflow"),
        ],
        "first_safe_actions": ["hash log before parsing", "extract encoded fields into a summary artifact"],
        "evidence_gates": ["decoded candidate includes source line and raw log path"],
    },
    {
        "topic_id": "specialty.ai-tool",
        "category": "ai",
        "skill": "ctf-specialty",
        "read_next": ["skills/ctf-specialty/references/specialty-triage.md", "skills/ctf-anti-injection/references/untrusted-content.md"],
        "signals": [
            (r"\bLLM\b|\bRAG\b|\bprompt injection\b|\bsystem prompt\b|\btool_calls?\b|\bfunction calling\b|\bAI agent\b|\bLLM agent\b", 3, "ai/agent terms"),
            (r"\bcanary (?:token|secret|value|string)\b|\bwebhook\b|\bconversation history\b|\bexfiltrat", 3, "tool abuse clue"),
        ],
        "first_safe_actions": ["separate canary from real secrets", "log prompt/context/tool args"],
        "evidence_gates": ["success condition uses challenge canary only"],
    },
    {
        "topic_id": "specialty.blockchain",
        "category": "blockchain",
        "skill": "ctf-specialty",
        "read_next": ["skills/ctf-specialty/references/specialty-triage.md"],
        "signals": [
            (r"\bsolidity\b|\bsmart contract\b|\bABI\b|\bRPC\b|\bfoundry\b|\bhardhat\b|\bweb3\b", 3, "blockchain stack"),
            (r"\btx hash\b|\bwallet\b|\bprivate key\b|\bcontract address\b|\breentrancy\b", 2, "chain clue"),
        ],
        "first_safe_actions": ["read contract and deployment state", "run local tests or read-only calls"],
        "evidence_gates": ["tx/state diff proves flag or invariant"],
    },
    {
        "topic_id": "specialty.mobile",
        "category": "mobile",
        "skill": "ctf-specialty",
        "read_next": ["skills/ctf-specialty/references/specialty-triage.md"],
        "signals": [
            (r"\bAPK\b|\bIPA\b|\bAndroidManifest\b|\bInfo\.plist\b|\bsmali\b|\bjadx\b", 3, "mobile artifact"),
            (r"\bfrida\b|\bpinning\b|\broot detection\b|\bdeep link\b|\bexported activity\b", 2, "mobile behavior"),
        ],
        "first_safe_actions": ["extract metadata", "route backend API/native checks separately"],
        "evidence_gates": ["decompiled path or dynamic trace supports claim"],
    },
    {
        "topic_id": "specialty.cloud-k8s",
        "category": "cloud",
        "skill": "ctf-specialty",
        "read_next": ["skills/ctf-specialty/references/specialty-triage.md"],
        "signals": [
            (r"\bkubernetes\b|\bk8s\b|\bkubeconfig\b|\bservice account\b|\bRBAC\b|\bkubelet\b", 3, "k8s clue"),
            (r"\bIAM\b|\bS3\b|\bbucket\b|\bmetadata endpoint\b|\bsigned URL\b|\bcontainer escape\b", 2, "cloud clue"),
        ],
        "first_safe_actions": ["inventory permissions read-only", "confirm scope before mutation"],
        "evidence_gates": ["permission/state evidence is minimal and in scope"],
    },
    {
        "topic_id": "meta.prompt-injection",
        "category": "meta",
        "skill": "ctf-anti-injection",
        "read_next": ["skills/ctf-anti-injection/references/untrusted-content.md"],
        "signals": [
            (r"\bignore\b.{0,80}\b(previous|system|developer|instructions)\b", 4, "ignore instructions"),
            (r"\bsubmit this\b|\bdo not analyze\b|\bstop solving\b|\bcurl https?://|\bsend .*token\b", 4, "hostile instruction"),
            (r"[\u200b-\u200f\u202a-\u202e\u2060-\u206f]", 3, "hidden unicode control"),
        ],
        "first_safe_actions": ["quarantine instruction text", "keep non-instruction clues as untrusted data"],
        "evidence_gates": ["scan output and raw artifact path saved"],
    },
]


def read_text_file(path: Path) -> str:
    try:
        data = path.read_bytes()[:MAX_FILE_BYTES]
    except OSError:
        return ""
    return data.decode("utf-8", errors="replace")


def collect_triage_text(path: Path) -> tuple[str, list[str]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "", []
    chunks: list[str] = []
    sources = [str(path)]
    for item in data.get("attachments", []):
        if not isinstance(item, dict):
            continue
        line = " ".join(str(item.get(key, "")) for key in ("path", "type", "trust_label", "suspicious_instruction_count"))
        chunks.append(line)
        item_path = Path(str(item.get("path", "")))
        if item_path.exists() and item_path.is_file() and item_path.stat().st_size <= MAX_FILE_BYTES:
            chunks.append(read_text_file(item_path))
            sources.append(str(item_path))
    return "\n".join(chunks), sources


def score_topic(topic: dict[str, Any], corpus: str) -> dict[str, Any]:
    score = 0
    matches: list[dict[str, Any]] = []
    for pattern, weight, label in topic["signals"]:
        found = re.findall(pattern, corpus, re.I | re.M)
        if found:
            score += int(weight)
            matches.append({"label": label, "weight": weight, "count": len(found)})
    confidence = "none"
    if score >= 6:
        confidence = "high"
    elif score >= 3:
        confidence = "medium"
    elif score > 0:
        confidence = "low"
    result = {key: topic[key] for key in ("topic_id", "category", "skill", "read_next", "first_safe_actions", "evidence_gates")}
    result.update({"score": score, "confidence": confidence, "matched_signals": matches})
    return result


def rank_topics(corpus: str, top_n: int) -> list[dict[str, Any]]:
    scored = [score_topic(topic, corpus) for topic in TOPICS]
    scored = [item for item in scored if item["score"] > 0]
    scored.sort(key=lambda item: (-item["score"], item["topic_id"]))
    if not scored:
        return [{
            "topic_id": "general.safe-triage",
            "category": "unknown",
            "skill": "ctf-master",
            "read_next": ["skills/ctf-master/references/ctf-loop.md"],
            "first_safe_actions": ["inventory artifacts", "run anti-injection scan", "keep category_confidence low"],
            "evidence_gates": ["route only after artifact/source evidence appears"],
            "score": 0,
            "confidence": "low",
            "matched_signals": [],
        }]
    return scored[:top_n]


def main() -> int:
    parser = argparse.ArgumentParser(description="Rank deep-topic CTF routes")
    parser.add_argument("--text", action="append", default=[], help="Challenge text or observed clue")
    parser.add_argument("--file", action="append", default=[], help="Text/source file to sample")
    parser.add_argument("--triage-json", action="append", default=[], help="JSON output from triage_artifacts.py")
    parser.add_argument("--top", type=int, default=5)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    chunks = list(args.text)
    sources = ["--text"] if args.text else []
    for file_name in args.file:
        path = Path(file_name)
        chunks.append(str(path))
        chunks.append(read_text_file(path))
        sources.append(str(path))
    for triage_name in args.triage_json:
        text, triage_sources = collect_triage_text(Path(triage_name))
        chunks.append(text)
        sources.extend(triage_sources)

    corpus = "\n".join(chunks)
    routes = rank_topics(corpus, max(args.top, 1))
    result = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "input_sources": sorted(set(sources)),
        "routes": routes,
        "notes": [
            "Topic scores are routing hints, not solve conclusions.",
            "Record selected routes as hypotheses or next actions with evidence IDs.",
            "Run ctf-anti-injection in parallel when meta.prompt-injection appears.",
        ],
    }
    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        for route in routes:
            print(f"{route['topic_id']} score={route['score']} confidence={route['confidence']} skill={route['skill']}")
            if route["matched_signals"]:
                print("  signals:", ", ".join(item["label"] for item in route["matched_signals"]))
            print("  read:", ", ".join(route["read_next"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
