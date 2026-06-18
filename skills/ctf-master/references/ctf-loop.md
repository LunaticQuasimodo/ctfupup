# CTF Work Loop

Use this loop for any non-trivial challenge.

## Loop

1. **Intake**: parse challenge and scope.
2. **Preflight**: check tools, network, Docker, browser, debugger, and OOB needs.
3. **Triage**: identify files, services, formats, language, protections, and likely category.
4. **Hypothesize**: write 2-5 testable paths, each tied to evidence.
5. **Experiment**: run the smallest tool/action that can confirm or deny one hypothesis.
6. **Summarize**: save raw output, extract key lines, update state.
7. **Checkpoint**: render `scripts/checkpoint_state.py` before context compression, long pauses, handoff prep, or strategy pivots.
8. **Route**: continue, switch category, search, or handoff.
9. **Verify**: confirm candidate flag or solve path independently.
10. **Report**: write reproducible steps and lessons.

## Attempt Budget

## Stuck Classification

When stuck, classify the blocker before asking for help:

- Continue: evidence exists, but code/output has not been fully analyzed.
- Search: unknown technology, specific CVE, framework version, protocol, file format, or algorithm appears.
- Switch tool: current tool cannot expose the needed view; browser, debugger, decompiler, solver, or GUI is more appropriate.
- Human intervention: authorization, credentials, VPN, license, hardware, platform outage, GUI-only judgment, or rule-sensitive action blocks progress.
- Handoff: three evidenced branches failed and the next move is strategy choice.

Do not repeat a command just because it failed. Retry only if the failure class changes:

- bad input fixed
- dependency installed
- target came back online
- timeout/rate adjusted
- stronger hypothesis formed

After three dead ends with good evidence, create a handoff or ask a focused strategy question.

## Context Compression

Use `scripts/checkpoint_state.py /path/to/ctf-state.json --out checkpoint.md` whenever the run is paused, the context is getting large, or another agent/human may resume.

For every long artifact, keep:

- raw path
- extraction command
- 5-20 key lines
- why those lines matter
- what to do next

Never paste entire disassemblies, logs, packet dumps, fuzz outputs, or payload dictionaries into the main context.
