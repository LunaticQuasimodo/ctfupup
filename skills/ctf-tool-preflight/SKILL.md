---
name: ctf-tool-preflight
description: CTF tool engineering and environment preflight skill. Use before running security tools, checksec, GDB/pwndbg, IDA/Ghidra, MCP servers, scanners, debuggers, browser automation, Docker/VM/VPN/proxy/OOB flows, or when tools fail, output too much, require version checks, need dry-runs, or must be wrapped as repeatable ToolCards with logging and context compression.
---

# CTF Tool Preflight

Use this before expensive, noisy, stateful, GUI, networked, or fragile tools. The goal is to prevent wasted attempts caused by missing dependencies, wrong target, overlong output, unsafe scope, or silent misconfiguration.

## Preflight Gate

Before a tool call, establish:

- Purpose: what question will this tool answer?
- Scope: local file, local container, authorized remote endpoint, or challenge-provided host.
- Inputs: file paths, host/port, credentials, wordlist, timeout, rate.
- Safety: scan limits, destructive risk, data exposure risk.
- Health: binary exists, version acceptable, minimal dry-run passes.
- Output plan: raw output path, summary extraction method, sensitive-data masking.

## ToolCard Pattern

Use `references/tool-cards.md` when creating or repairing a ToolCard. Each ToolCard needs:

- Applies when.
- Do not use when.
- Preflight command.
- Minimal example.
- Expected output.
- Common failures.
- Retry strategy.
- Context compression rule.
- Risk notes.

## Recommended Script

Run:

```bash
python3 scripts/ctf_preflight.py --profile general --json
python3 scripts/ctf_preflight.py --profile web --json
python3 scripts/ctf_preflight.py --profile pwn-rev --json
python3 scripts/ctf_preflight.py --profile forensics-crypto --json
```

The script checks common local tools and emits JSON suitable for `CTFRunState.environment`.

## Output Compression

For commands expected to exceed 200 lines:

1. Save raw output to `artifacts/raw/<tool>-<timestamp>.txt`.
2. Extract key lines into `artifacts/summaries/<tool>-<timestamp>.md`.
3. Only load the summary unless raw evidence is needed.
4. Keep hashes or byte offsets for binary artifacts.

## Failure Classification

Classify failure before retrying:

- `wrong_tool`: tool cannot answer the question.
- `bad_input`: path/host/parameter/protocol wrong.
- `missing_dependency`: binary, library, license, GUI, VM, container missing.
- `target_unavailable`: host down, VPN/proxy/DNS issue.
- `rate_or_scope`: scan blocked by rules or likely too noisy.
- `hypothesis_wrong`: tool worked but contradicted the idea.
- `output_overload`: tool worked but needs better filtering.

## References

Read when needed:

- `references/tool-cards.md`: tool cards for common CTF tools.
- `references/environment-preflight.md`: VPN/OOB/Docker/browser/GUI checklist.
- `references/mcp-adapters.md`: MCP, browser, IDA, CTFd, HexStrike, sqlmap, pwntools safety notes.
