---
name: ctf-handoff-report
description: CTF handoff, stuck recovery, writeup, solve log, and post-solve reflection skill. Use when Codex is stuck, needs human or other-model takeover, must summarize current state, produce a final CTF writeup, generate reproducible steps, package evidence, or reflect on failed paths and skill improvements.
---

# CTF Handoff and Report

Use this instead of vague status updates. Its job is to make the next human or agent faster than starting over.

## When To Handoff

Create a handoff when:

- Environment, VPN, credentials, GUI, license, hardware, or platform access blocks progress.
- Three or more well-evidenced branches fail and the next choice is strategic.
- The challenge needs human visual/interactive judgment.
- Context is large and another model/human should continue.
- A risky action needs explicit human authorization.

## When To Writeup

Write a report when:

- Flag is found and verified.
- A partial solve needs preservation.
- The user asks for复盘/writeup/report.
- Skills should be improved based on the run.

## Required Handoff Fields

Use `references/handoff-template.md` and include:

- Challenge profile.
- Environment and tool status.
- Current state summary.
- Evidence table.
- Attempts and dead ends.
- Current hypotheses.
- Most likely next actions.
- Questions for human.
- Raw artifact paths.
- Safety/scope notes.

## Required Writeup Fields

Use `references/writeup-template.md` and include:

- Challenge overview.
- Initial triage.
- Key observations.
- Exploit/solve path.
- Commands/scripts.
- Flag verification.
- What failed and why.
- Lessons and skill updates.

## Reflection Loop

After handoff/writeup, add a short improvement section:

- Which tool failed due to preflight gaps?
- Which state field was missing?
- Which reference should become a ToolCard/checklist?
- Which false positive or fake clue should be added to anti-injection rules?

Use `scripts/render_handoff.py` to render a JSON state file into a Markdown handoff draft. Use `scripts/render_writeup.py` to render a concise writeup draft from the same state. Use `scripts/render_reflection.py` after a run to turn friction, dead ends, evidence gaps, and suspicious content into concrete skill-improvement candidates. Use `scripts/finalize_run.py` to package validation, state, handoff, writeup, reflection, and a manifest for handoff or archive.
