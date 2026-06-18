# Requirements Traceability

This matrix maps the original Chinese research request, the phase-one plan, and the three requested reference skill sources to concrete suite artifacts. It is intentionally evidence-oriented: a requirement is not marked covered unless local files provide direct proof.

## Status

- `covered`: current artifacts directly satisfy the requirement.
- `partial`: useful artifacts exist, but the requirement is not fully proven.
- `open`: required evidence is missing.

## Route Comparison

The suite implements the short/mid-term hybrid route: mature code agent + installable skills + deterministic scripts + MCP/tool adapters + state/evidence discipline. A fully dedicated CTF agent with multi-queue scheduling, custom sandboxes, and centralized solve database remains a later system option. The hybrid route is favored now because it is portable across Claude Code, Codex, Cursor, Gemini CLI-like tools, and other skill-compatible agents while avoiding a large custom orchestration surface before real solve data justifies it.

## Current Gate Requirements

| ID | Requirement | Status | Primary Evidence |
|---|---|---|---|
| `REQ-BOUNDARY-001` | Legal CTF / authorized lab / isolated environment boundary | covered | `skills/ctf-master/SKILL.md`, `SKILL_SUITE.md` |
| `REQ-TOOLS-001` | Avoid wasted time on tool config, failures, long output, repeated attempts | covered | `ctf-tool-preflight`, `summarize_output.py`, ToolCards |
| `REQ-INTAKE-002` | Quickly know what to inspect, run, and verify after challenge intake | covered | `ctf-master`, `deep-topic-router.md`, `route_topic.py` |
| `REQ-KNOWLEDGE-003` | Precise, non-overloading knowledge retrieval and distillation | covered | `ctf-knowledge`, `seed-source-matrix.md` |
| `REQ-SOURCE-MATRIX-017` | Auditable borrowed-design / do-not-copy / conversion evidence for requested references | covered | `audit_source_matrix.py`, `seed-source-matrix.md`, `release_gate.py` |
| `REQ-REFERENCE-PROVENANCE-020` | Source anchor, observed signal, and review-date provenance for absorbed references | covered | `audit_source_matrix.py`, `seed-source-matrix.md`, `tests/test_scripts.py` |
| `REQ-STATE-004` | Maintain a CTF state machine instead of retrying blindly | covered | `state-schema.md`, `init_state.py`, `update_state.py`, `validate_state.py` |
| `REQ-PROFILE-015` | Deterministic ChallengeProfile updates without manual JSON editing | covered | `update_profile.py`, `audit_quality.py`, `tests/test_scripts.py` |
| `REQ-STUCK-005` | Classify stuck states and recovery choices | covered | `ctf-loop.md`, `acceptance-gates.md`, `ctf-handoff-report` |
| `REQ-HANDOFF-006` | Fixed handoff template for humans or other models | covered | `handoff-template.md`, `render_handoff.py`, `render_reflection.py`, `finalize_run.py` |
| `REQ-CHECKPOINT-012` | Deterministic checkpoint/context-compression artifact for pause/resume/handoff | covered | `checkpoint_state.py`, `ctf-loop.md`, `finalize_run.py` |
| `REQ-PHASE-GATE-014` | Executable CTF run phase gates for scope, triage, route, experiment, verification, report, and handoff readiness | covered | `gate_state.py`, `phase-gates.md`, `audit_quality.py`, `tests/test_scripts.py` |
| `REQ-ANTI-007` | Defend against prompt injection, fake flags, hidden/long-text/tool traps, and unsafe verbatim replay | covered | `ctf-anti-injection`, `untrusted-content.md`, `scan_untrusted_text.py` |
| `REQ-ENV-008` | Preflight VPS/OOB/VPN/Docker/VM/GUI/browser/IDA/proxy/network needs | covered | `environment-preflight.md`, `ctf_preflight.py`, `mcp-adapters.md` |
| `REQ-SKILLS-009` | Layered, triggerable, maintainable, testable skills | covered | `suite-manifest.json`, `SKILL_SUITE.md`, `validate_suite.py` |
| `REQ-AGENT-METADATA-016` | Validate `agents/openai.yaml` UI/default-prompt metadata | covered | `audit_agent_metadata.py`, `release_gate.py`, `tests/test_scripts.py` |
| `REQ-ROUTE-010` | Compare code-agent skills vs dedicated agent vs hybrid route | covered | route comparison above, `seed-source-matrix.md` |
| `REQ-QUALITY-011` | Executable quality/reflection gate for professional skill artifacts | covered | `audit_quality.py`, `audit_pressure.py`, `release_gate.py`, `tests/test_scripts.py` |
| `REQ-PRESSURE-AUDIT-024` | Machine-readable hard-question pressure audit with failure modes, accepted gaps, future watch items, and next actions | covered | `audit_pressure.py`, `audit_quality.py`, `tests/test_scripts.py` |
| `REQ-COMPLETION-AUDIT-022` | Separate engineering readiness from final v1 completion proof | covered | `audit_completion.py`, `release_gate.py`, `suite-manifest.json` |
| `REQ-TRIGGER-013` | Deterministic skill trigger/conflict audit | covered | `audit_triggers.py`, `audit_quality.py`, `tests/test_scripts.py` |
| `REQ-FORWARD-INTEGRITY-018` | Forward-test prompt packs and run-record templates avoid expected-answer leakage | covered | `audit_forward_integrity.py`, `run_forward_suite.py`, `release_gate.py` |
| `REQ-FORWARD-RUN-INIT-019` | Deterministic fresh-agent forward-test workspace initialization | covered | `init_forward_run.py`, `forward-tests/README.md`, `release_gate.py` |
| `REQ-FORWARD-RUBRIC-023` | Deterministic fresh-agent human-rubric template generation | covered | `render_forward_rubric.py`, `init_forward_run.py`, `tests/test_scripts.py` |
| `REQ-FORWARD-HANDOFF-025` | Answer-free fresh-agent handoff packet with prompt paths, response rules, and hashes | covered | `render_forward_handoff.py`, `init_forward_run.py`, `verify_forward_run.py`, `tests/test_scripts.py` |
| `REQ-FRESH-AGENT-READINESS-026` | Pre-run readiness audit for prompt hashes, handoff, record, rubric, runbook, empty responses, and leak terms | covered | `audit_fresh_agent_readiness.py`, `release_gate.py`, `tests/test_scripts.py` |
| `REQ-FRESH-AGENT-PACKET-027` | Minimal fresh-agent launch packet with handoff, response rules, packet manifest, and prompts only | covered | `export_fresh_agent_packet.py`, `release_gate.py`, `tests/test_scripts.py` |
| `REQ-FRESH-AGENT-PACKET-AUDIT-028` | Independent verification of exported packet files, hashes, manifest, forbidden files, and leak terms | covered | `audit_fresh_agent_packet.py`, `release_gate.py`, `tests/test_scripts.py` |
| `REQ-FRESH-AGENT-LAUNCH-PROMPT-029` | Copy-paste launch prompt generated from audited packet plus allowed local skill root | covered | `render_fresh_agent_launch_prompt.py`, `release_gate.py`, `tests/test_scripts.py` |
| `REQ-FRESH-AGENT-SKILL-ROOT-033` | Fresh-agent launch permits the local skill root while excluding scoring, run records, scenario JSON, and prior analysis | covered | `export_fresh_agent_packet.py`, `render_fresh_agent_launch_prompt.py`, `audit_fresh_agent_packet.py`, `tests/test_scripts.py` |
| `REQ-FORWARD-RUN-FINALIZE-021` | Deterministic fresh-agent response scoring, hashing, rubric merge, and record finalization | covered | `finalize_forward_run.py`, `verify_forward_run.py`, `tests/test_scripts.py` |
| `REQ-RELEASE-CONSISTENCY-030` | Release-level manifest, version, validation command, release gate, and traceability drift audit | covered | `audit_release_consistency.py`, `release_gate.py`, `tests/test_scripts.py` |
| `REQ-CATEGORY-COVERAGE-031` | Major category coverage audit across skills, routes, references, demos, forward tests, and benchmark gaps | covered | `audit_category_coverage.py`, `reverse-checker-decoy.json`, `release_gate.py`, `tests/test_scripts.py` |
| `REQ-EVIDENCE-CONTRACT-032` | Reproducible evidence contract for handoff, writeup, raw artifacts, contrast checks, verification, and verdict-style separation | covered | `audit_evidence_contract.py`, `writeup-template.md`, `render_writeup.py`, `tests/test_scripts.py` |
| `REQ-REF-SRC-HUNTER` | Absorb src-hunter checkpoint/scope/evidence/playbook discipline | covered | `seed-source-matrix.md`, `REFLECTION_AUDIT.md` |
| `REQ-REF-HACK-SKILLS` | Absorb hack-skills master/category/deep-topic routing | covered | `deep-topic-router.md`, `route_topic.py` |
| `REQ-REF-RED-TEAM` | Absorb runner/tricks/bypass/verdict gates and evidence discipline | covered | `REFLECTION_AUDIT.md`, `state-schema.md`, ToolCards |
| `REQ-INTERFACES` | Define ChallengeProfile, ToolCard, CTFRunState, EvidenceRecord, HandoffPacket | covered | `state-schema.md`, `tool-card-template.md` |
| `REQ-PHASE-ONE` | Preserve phase-one framework contract | covered | `SKILL_SUITE.md`, `REFLECTION_AUDIT.md` |
| `REQ-PHASE-TWO-REPORT` | Complete standalone research report | covered | `research/phase-two-research-report.md` |
| `REQ-PHASE-THREE-SKILLS` | Produce installable layered skills with scripts/tests/install/audit | covered | `suite-manifest.json`, `install.sh`, `tests/test_scripts.py` |
| `REQ-EVAL-REAL-CTF` | Real or benchmark CTF end-to-end validation | covered | `benchmarks/runs/cybench-primary-knowledge`, `verify_benchmark_run.py` |

## V1 Targets Not Yet Proven

| ID | Requirement | Status | Missing Proof |
|---|---|---|---|
| `REQ-EVAL-FRESH-AGENT` | Fresh-agent forward-test without leaked expected answers | partial | Fresh-agent iterations v1-v3 produced useful regressions, v4 packet is ready, and the final v4 rerun is explicitly user-waived; strict verified pass remains reopenable. |

## Audit Command

Run:

```bash
python3 scripts/audit_traceability.py --root . --json
```

The audit fails only when a `current_gate` requirement lacks declared evidence or when a requirement marked `covered` has missing evidence. `v1_target` gaps are reported as non-failing findings so the suite can remain installable while preserving honest completion criteria.
