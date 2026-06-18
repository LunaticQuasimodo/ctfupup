# Common CTF ToolCards

Every ToolCard must state allowed tools, preflight, minimal command, failure handling, retry rules, output handling, and compression rules. If a tool would require destructive, high-volume, or out-of-scope behavior, stop and use the human intervention gate.

## Required Fields

- Applies when: precise task/signal that justifies the tool.
- Allowed tools: exact binary, MCP, script, or browser capability permitted for this card.
- Preflight: health/version/dependency check before real use.
- Minimal command: smallest evidence-producing invocation.
- Failure: tool_not_found, bad_argument, dependency_missing, target_unavailable, scope_or_rate_limit, output_overload, or hypothesis_failed.
- Retry: retry only after the failure class changes.
- Output handling: save raw output first, then summarize high-signal facts.
- Compression: keep paths, key lines, counts, anomalies, candidate flags, and next action.

## nmap

- Applies when: authorized remote host/port enumeration is needed.
- Allowed tools: `nmap` only.
- Preflight: `nmap --version`.
- Minimal: `nmap -sV -Pn -p PORTS HOST -oN artifacts/raw/nmap.txt`.
- Failure: tool_not_found, bad_argument, target_unavailable, scope_or_rate_limit.
- Retry: reduce ports or timing only when rules allow and the failure class changes.
- Output handling: save full `-oN` output.
- Do not use broad scans unless rules allow.
- Compress: open ports, service/version, scripts with anomalies.

## ffuf

- Applies when: focused web path/parameter discovery is needed.
- Allowed tools: `ffuf` only.
- Preflight: `ffuf -V`.
- Minimal: `ffuf -u URL/FUZZ -w WORDLIST -mc 200,301,302,403 -t 10 -o artifacts/raw/ffuf.json -of json`.
- Failure: rate_or_scope, target_unavailable, output_overload.
- Retry: lower threads, narrow wordlist, or adjust matchers only after a baseline response is saved.
- Output handling: preserve JSON; never paste full result sets into context.
- Compress: status/path/length/words/redirect.

## curl

- Applies when: reproducible HTTP baseline or PoC is needed.
- Allowed tools: `curl` only.
- Preflight: `curl --version`.
- Minimal: `curl -i -sS --max-time 10 URL -o artifacts/raw/curl-response.txt`.
- Failure: bad_url, tls_error, timeout, auth_missing, target_unavailable.
- Retry: change one variable at a time and keep comparison artifacts.
- Output handling: save headers and body together for baseline requests.
- Compress: status, headers, set-cookie names, body clues.

## gdb/pwndbg

- Applies when: crash, offset, register, heap, or dynamic reverse proof is needed.
- Allowed tools: `gdb`, `pwndbg`, and local binary only.
- Preflight: `gdb --version`; `python3 -c 'import pwn'` if pwntools used.
- Minimal: run binary with controlled input and save crash/backtrace.
- Failure: architecture_mismatch, missing_symbols, no_crash, input_not_reaching_sink.
- Retry: change input or debugging setup only when the hypothesis changes.
- Output handling: save backtrace/registers/disassembly snippets to raw artifacts.
- Risk: GUI/terminal state, architecture mismatch.

## tshark

- Applies when: PCAP command-line extraction is needed.
- Allowed tools: `tshark` only.
- Preflight: `tshark -v`.
- Minimal: `tshark -r capture.pcap -q -z io,phs`.
- Failure: unsupported_capture, missing_keylog, output_overload.
- Retry: filter by protocol/conversation after protocol inventory.
- Output handling: export objects to files; keep packet filters and counts.
- Compress: protocols, conversations, exported objects, suspicious filters.

## binwalk

- Applies when: embedded files or firmware-like blobs.
- Allowed tools: `binwalk` for inspection; extraction only after risk review.
- Preflight: `binwalk --help`.
- Minimal: `binwalk FILE`.
- Failure: unsupported_signature, extraction_risk, dependency_missing.
- Retry: try file/carving tools only after source hash is saved.
- Output handling: save signature table and extracted paths.
- Risk: extraction may run external decompressors; inspect before executing extracted files.

## z3/sage

- Applies when: constraints/equations are known.
- Allowed tools: `python3` with `z3`, or `sage`.
- Preflight: `python3 -c 'import z3'` or `sage --version`.
- Failure: variables_undefined, bounds_wrong, solver_timeout, unverifiable_result.
- Retry: simplify constraints or add bounds after writing assumptions.
- Output handling: save solver script and verification output.
- Do not use before defining variables, bounds, and verification.
