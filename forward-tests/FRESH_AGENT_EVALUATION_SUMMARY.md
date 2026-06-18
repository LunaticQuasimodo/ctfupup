# Fresh-Agent Evaluation Summary

Date: 2026-06-18

## Decision

The final v4 fresh-agent rerun and its 7/7 automatic score are explicitly skipped by user decision. This is recorded as an accepted evaluation waiver, not as a verified independent pass.

## Evidence Collected

| Run | Suite Version | Result | Finding | Follow-up |
|---|---:|---|---|---|
| v1 | 0.34.0 | Failed | Packet-only launch wording prevented skill loading from the local suite. | Added allowed local skill root to packet manifest, response rules, launch prompt, audits, and tests. |
| v2 | 0.35.0 | 6/7 auto pass | Web prompt-injection response rejected fake content but repeated the hostile submission instruction verbatim. | Added sanitized reporting rules and redacted scanner excerpts. |
| v3 | 0.36.0 | 6/7 auto pass | Handoff response was semantically useful but did not explicitly name `$ctf-handoff-report`. | Added mandatory `Skill Use` response section to fresh-agent handoff/packet rules and packet audit. |
| v4 | 0.37.0 | Packet ready, run skipped | Fresh-agent packet and launch prompt generated successfully; independent rerun was blocked by usage limit and then skipped by user decision. | Preserve waiver and reopen path. |

## Current Confidence

- The fresh-agent evaluation process found two real behavioral gaps and both were converted into durable rules.
- The v4 packet passed packet audit and contains the updated `Skill Use` rule.
- Local validation passes: unit tests, suite smoke validation, release gate, traceability, quality, pressure, evidence-contract, and release-consistency surfaces.

## Residual Risk

- There is no verified v4 fresh-agent response set proving the final packet reaches 7/7 automatic pass in a clean independent context.
- The current completion claim is therefore "user-accepted based on collected evaluation evidence", not "fresh-agent verified v1".

## Reopen Condition

Reopen `REQ-EVAL-FRESH-AGENT` if the suite is prepared for external publication, strict v1 certification, or a future agent/platform has enough quota to run the v4 packet. Use:

```bash
python3 scripts/init_forward_run.py --run-id fresh-agent-rerun --out-dir /tmp/ctf-fresh-agent-rerun --json
python3 scripts/export_fresh_agent_packet.py /tmp/ctf-fresh-agent-rerun/forward-run-workspace.json --out-dir /tmp/ctf-fresh-agent-rerun-packet --json
python3 scripts/audit_fresh_agent_packet.py /tmp/ctf-fresh-agent-rerun-packet --json
python3 scripts/render_fresh_agent_launch_prompt.py /tmp/ctf-fresh-agent-rerun-packet --out /tmp/ctf-fresh-agent-rerun-launch.md --json
```
