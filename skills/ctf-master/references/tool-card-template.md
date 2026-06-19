# ToolCard Template

Use this when adding a tool to a repeatable CTF workflow.

## Fields

- `tool`: name and version command.
- `purpose`: question this tool answers.
- `applies_when`: evidence signals.
- `pause_or_adjust_when`: scope, noise, mismatch, or missing-evidence conditions that require tuning rather than banning the tool.
- `preflight`: command and expected result.
- `minimal_command`: safest useful invocation.
- `useful_tools`: preferred tool plus interchangeable MCP/CLI/script/browser alternatives.
- `inputs`: file/host/port/wordlist/session requirements.
- `outputs`: raw output path and summary fields.
- `success_signals`: what proves it answered the question.
- `failure_classes`: bad input, missing dependency, target unavailable, wrong tool, output overload, hypothesis wrong.
- `retry_strategy`: bounded and evidence-driven.
- `context_compression`: exact grep/filter/parser rules.
- `risk_notes`: destructive, privacy, scan-rate, or credential risks.

## Example Skeleton

```yaml
tool: ffuf
purpose: discover likely challenge endpoints without broad uncontrolled crawling
applies_when:
  - authorized web target
  - endpoint inventory missing
pause_or_adjust_when:
  - rules forbid brute force
  - target is production-like and no rate limit is approved
useful_tools:
  - ffuf
  - feroxbuster
  - gobuster
  - Burp Suite content discovery
  - HexStrike/security-tool MCP web discovery module
preflight:
  command: ffuf -V
minimal_command:
  command: ffuf -u https://HOST/FUZZ -w WORDLIST -mc 200,301,302,403 -t 10 -o artifacts/raw/ffuf.json -of json
outputs:
  raw: artifacts/raw/ffuf.json
  summary: status, path, length, words, redirect
failure_classes:
  - target_unavailable
  - rate_or_scope
  - output_overload
risk_notes:
  - keep thread count and wordlist small unless rules allow more
```
