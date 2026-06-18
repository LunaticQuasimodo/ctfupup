# Reflection Audit

This audit pressure-tests the suite against the original research goal and the reference skills.

## What Was Absorbed

From `src-hunter-skill`:

- Checkpoint workflow instead of free-form advice.
- Scope gate before active testing.
- Evidence discipline: no conclusion without reproducible proof.
- Evidence contract: reproducible evidence, raw artifacts, contrast checks, and verification stay linked in reports.
- Progressive disclosure: load playbooks/references only when signals match.

From `yaklang/hack-skills`:

- Master -> category -> deep topic routing.
- Security knowledge distilled into signal tables and checklists.
- Avoiding tiny one-off skills that create router noise.
- Treating payload catalogs as references, not primary prompt context.

From local `red_team_skill`:

- Runner/tricks/bypass/verdict separation.
- Strong gates before conclusions.
- Tool whitelist and preflight thinking.
- Structured evidence and raw-output preservation.
- Context protection against huge tool output.
- Verdict-style separation: conclusions consume evidence records rather than rerunning or guessing.

## Coverage Audit

| Requirement | Current Artifact |
|---|---|
| Master skill | `skills/ctf-master/SKILL.md` |
| Web category | `skills/ctf-web/SKILL.md` |
| Pwn/Reverse category | `skills/ctf-pwn-rev/SKILL.md` |
| Crypto/Forensics/Misc category | `skills/ctf-forensics-crypto/SKILL.md` |
| Blockchain/AI/Mobile/IoT/Cloud category | `skills/ctf-specialty/SKILL.md` |
| Tool adapter/preflight | `skills/ctf-tool-preflight/` |
| Knowledge distillation | `skills/ctf-knowledge/` |
| Anti-adversarial safety | `skills/ctf-anti-injection/` |
| Handoff/writeup/report | `skills/ctf-handoff-report/` |
| State schema | `ctf-master/references/state-schema.md` |
| Profile updater | `ctf-master/scripts/update_profile.py` |
| Phase gates | `ctf-master/references/phase-gates.md`, `ctf-master/scripts/gate_state.py` |
| Deep topic routing | `ctf-master/references/deep-topic-router.md`, `ctf-master/scripts/route_topic.py` |
| Scripts | `init_state.py`, `update_profile.py`, `update_state.py`, `validate_state.py`, `gate_state.py`, `checkpoint_state.py`, `triage_artifacts.py`, `route_topic.py`, `redact_text.py`, `summarize_output.py`, `ctf_preflight.py`, `scan_untrusted_text.py`, `source_matrix.py`, `render_handoff.py`, `render_writeup.py`, `render_reflection.py`, `finalize_run.py`, `score_forward_test.py`, `run_forward_suite.py`, `init_forward_run.py`, `render_forward_rubric.py`, `render_forward_handoff.py`, `audit_fresh_agent_readiness.py`, `export_fresh_agent_packet.py`, `audit_fresh_agent_packet.py`, `render_fresh_agent_launch_prompt.py`, `finalize_forward_run.py`, `verify_forward_run.py`, `audit_completion.py`, `audit_pressure.py`, `audit_category_coverage.py`, `audit_evidence_contract.py`, `audit_release_consistency.py`, `audit_source_matrix.py`, `audit_forward_integrity.py`, `audit_triggers.py`, `init_benchmark_run.py`, `verify_benchmark_run.py`, `release_gate.py` |
| Install/test guidance | `SKILL_SUITE.md` |
| Suite validation | `scripts/validate_suite.py`, `scripts/release_gate.py` |
| Quality audit | `scripts/audit_quality.py` |
| Pressure audit | `scripts/audit_pressure.py` |
| Category coverage audit | `scripts/audit_category_coverage.py` checks core and specialty CTF coverage plus future benchmark coverage gaps |
| Evidence contract audit | `scripts/audit_evidence_contract.py` checks EvidenceRecord reproducibility, report evidence references, raw artifacts, contrast checks, verification text, and verdict-style separation |
| Release consistency audit | `scripts/audit_release_consistency.py` checks manifest skill inventory, validation command paths, release gate coverage, version status, and traceability doc sync |
| Completion audit | `scripts/audit_completion.py` separates engineering readiness from v1 proof |
| Source matrix audit | `scripts/audit_source_matrix.py` with source-anchor, observed-signal, and review-date provenance checks |
| Forward integrity audit | `scripts/audit_forward_integrity.py` |
| Agent metadata audit | `scripts/audit_agent_metadata.py` |
| Trigger/conflict audit | `scripts/audit_triggers.py` |
| Installation helper | `install.sh` |
| Forward-test scenarios | `forward-tests/` |
| Forward-test runner | `scripts/run_forward_suite.py` |
| Forward-run initializer | `scripts/init_forward_run.py` |
| Forward-run rubric template | `scripts/render_forward_rubric.py`, generated `rubric-template.json` |
| Forward-run sealed handoff | `scripts/render_forward_handoff.py`, generated `FRESH_AGENT_HANDOFF.md` |
| Fresh-agent readiness audit | `scripts/audit_fresh_agent_readiness.py` checks prompt hashes, handoff, record, rubric, runbook, empty responses, and leak terms |
| Fresh-agent minimal packet | `scripts/export_fresh_agent_packet.py` exports `FRESH_AGENT_HANDOFF.md`, `RESPONSE_RULES.md`, `PACKET_MANIFEST.json`, and prompt files only |
| Fresh-agent packet verifier | `scripts/audit_fresh_agent_packet.py` verifies required files, forbidden files, prompt hashes, manifest consistency, and leak terms after export |
| Fresh-agent launch prompt | `scripts/render_fresh_agent_launch_prompt.py` renders a copy-paste prompt from the audited packet plus an allowed local skill root |
| Forward-test record finalizer/gate | `forward-tests/fresh-agent-run-record-template.json`, `scripts/finalize_forward_run.py`, `scripts/verify_forward_run.py` |
| Seed research matrix | `research/seed-source-matrix.md` |
| Phase-two research report | `research/phase-two-research-report.md` |
| Benchmark run scaffold | `benchmarks/benchmark-runbook.md`, `scripts/init_benchmark_run.py` |
| Verified benchmark run | `benchmarks/runs/cybench-primary-knowledge/`, `scripts/verify_benchmark_run.py` |
| Synthetic end-to-end demo | `demo-fixtures/` Web/Crypto/Reverse/Pwn/Forensics fixtures, `scripts/run_demo_solve.py --all` |

## Validation Snapshot

Recorded on 2026-06-18 for suite version `0.38.0`.

| Check | Result |
|---|---|
| Traceability audit | 43 requirements checked, 0 failing current gates, 1 non-failing v1 target still partial/open |
| Unit tests | 38 tests passed |
| Suite smoke validation | 9 skills validated |
| Quality audit | 30 quality checks passed for reference absorption, source matrix audit, progressive disclosure, routing, demo coverage, reflection loop, pressure audit, category coverage audit, evidence contract audit, release consistency audit, checkpoint discipline, profile update surface, phase-gate discipline, agent metadata, forward integrity, forward-run init, forward-run rubric, forward handoff, fresh-agent readiness, fresh-agent packet export, fresh-agent packet audit, fresh-agent launch prompt, forward-run finalize, validation isolation, completion audit, trigger audit, validation surface, and fresh-agent honesty |
| Pressure audit | Machine-readable hard questions, failure modes, evidence checks, accepted gap handling for `REQ-EVAL-FRESH-AGENT`, future watch items, and next actions |
| Category coverage audit | 9 category surfaces checked: 5 core categories and 4 specialty surfaces have skill, route, and reference coverage; web/pwn/reverse/forensics still need future benchmark coverage beyond synthetic/demo/forward evidence |
| Evidence contract audit | Report and handoff surfaces checked for reproducible evidence, raw artifacts, Evidence References, Contrast Checks, Verification, and verdict-style separation from unsupported conclusions |
| Release consistency audit | Manifest skill inventory, validation command script references, release-gate-critical checks, version status, and traceability JSON/Markdown IDs are checked together |
| Completion audit | `engineering_ok=true`; strict fresh-agent verification remains partial, while `fresh-agent-evaluation-waiver.json` can be supplied for user-accepted completion |
| Source matrix audit | 12 source rows checked; `src-hunter-skill`, `yaklang/hack-skills`, and local `red_team_skill` each have borrowed-design, do-not-copy, local-conversion, source-anchor, observed-signal, and review-date evidence |
| Forward integrity audit | 7 prompt-pack files checked for scoring-field and expected-answer leakage; run-record template starts as not-run evidence |
| Fresh-agent readiness audit | Generated workspace checked for prompt hashes, sealed handoff, not-run record, rubric template, runbook, empty response directory, and leak-term filters before launch |
| Fresh-agent packet export | Minimal packet contains handoff, response rules, packet manifest, and prompt files only; run records, rubric files, score output, workspace manifests, scenario JSON, and prior analysis are excluded |
| Fresh-agent packet audit | Exported packet checked independently for required files, forbidden files, prompt hash drift, manifest consistency, and forbidden leak terms |
| Fresh-agent launch prompt | Copy-paste prompt rendered from audited packet, pointing to handoff, response rules, prompt files, and the allowed local skill root |
| Fresh-agent skill-root boundary | First independent run found packet-only wording blocked skill loading; launch materials now allow local skill-root reads while still excluding scenario JSON, scoring, rubric, run records, workspace manifests, prior analysis, and development notes |
| Anti-injection safe reporting | Second independent run caught that rejecting a fake flag is not enough if the response repeats the hostile submission instruction verbatim; v0.36.0 requires sanitized paraphrases and redacted scanner excerpts |
| Fresh-agent skill-use reporting | Third independent run showed a semantically good handoff can omit the exact skill identity; v0.37.0 requires a `Skill Use` section in every fresh-agent response |
| Agent metadata audit | 9 `agents/openai.yaml` files validated for display name, short description, and `$skill` default prompt |
| Profile updater | `update_profile.py` updates scope/category/targets/rules/attachments with attachment hashes and feeds phase gates |
| Phase gate evaluator | `gate_state.py` blocks unsafe progress from unknown scope and verifies benchmark report readiness |
| Trigger/conflict audit | Skill frontmatter, forward scenarios, inline route probes, expected skills, and forbidden top-rank conflicts pass |
| Release gate | Local release gate passes with a per-run isolated workspace and only `REQ-EVAL-FRESH-AGENT` allowed as partial/open |
| Official skill validator | 9 skills valid |
| Synthetic demo | Web/Crypto/Reverse/Pwn/Forensics fixtures generated state, handoff, writeup, reflection, route topics, and expected candidate flags |
| Reflection renderer | `render_reflection.py` turns tool friction, evidence gaps, dead ends, and suspicious content into improvement candidates |
| Run finalizer | `finalize_run.py` packages validation, state, handoff, writeup, reflection, and manifest |
| Forward-suite runner | Scenario listing, prompt/response workflow, clean workspace initializer, rubric-template renderer, sealed fresh-agent handoff renderer, readiness auditor, minimal packet exporter, packet verifier, launch prompt renderer, response hashing finalizer, run-record template, and strict verifier available; v1-v3 independent runs produced regressions and the final v4 rerun is user-waived |
| Benchmark initializer | Synthetic smoke run creates profile, state, artifact dirs, and runbook |
| Benchmark verifier | Cybench Primary Knowledge run verified as `solved_oracle_validated` with 5 evidence records |
| State validator | `validate_state.py` checks schema, IDs, evidence references, scope, next-action limits, and strict artifact paths |
| Checkpoint renderer | `checkpoint_state.py` renders a compact resume snapshot with validation, facts, hypotheses, recent evidence, artifact paths, risks, and resume checklist |
| Install dry-run | Codex and Claude target copies listed successfully |
| Residue scan | No template markers found |

## Remaining Risks

- The suite is framework-level; it does not yet include deep payload playbooks for every vulnerability type. This is intentional to avoid context overload and copyright/payload bloat.
- `ctf-specialty` is broad. After real challenge use, split it if one subdomain becomes frequent enough.
- Tool availability varies heavily by machine. `ctf_preflight.py` reports missing tools but does not install them.
- Only one real benchmark task has been solved end-to-end so far: Cybench Primary Knowledge. This proves the run machinery, not broad solve-rate.
- Official validator required PyYAML; validation was run inside a temporary venv to avoid modifying the repo.
- Forward-test prompts are synthetic; they test behavior shape, not real exploit success.
- Final v4 fresh-agent rerun and 7/7 automatic score were skipped by explicit user decision after v1-v3 findings had already driven fixes; this is recorded as a waiver, not as strict verification.

## Next Iteration Triggers

Create or refine a reference when any of these happens twice:

- Same tool failure repeats.
- Same category route is ambiguous.
- Same long-output summary misses the key clue.
- Same fake flag or injected instruction appears.
- Same exploit/solver scaffold is rewritten.
- Same handoff question is asked by a human.

## Hard Questions For Future Runs

- Did the master skill force enough evidence before routing?
- Did a category skill make the next command obvious?
- Did preflight prevent a real wasted attempt?
- Did anti-injection catch hidden instructions without hiding useful clues?
- Did the handoff make another solver faster than starting over?
- Did the writeup preserve enough detail to reproduce the solve one week later?

## Completion Criteria For A Future "v1.0"

Already satisfied in the current suite:

- Record solve outcomes in `CTFRunState`.
- Update `ChallengeProfile` through a deterministic script rather than manual JSON edits.
- Validate `agents/openai.yaml` metadata after skill updates.
- Validate the source matrix after reference-source updates.
- Validate fresh-agent prompt packs before using them for independent forward tests.
- Initialize fresh-agent forward-test workspaces with deterministic prompt, response, manifest, record, and runbook paths.
- Generate a deterministic human rubric template for every fresh-agent forward-test workspace.
- Generate an answer-free fresh-agent handoff packet with prompt paths, hashes, and response rules.
- Run a pre-launch fresh-agent readiness audit over prompt hashes, handoff, record, rubric, runbook, empty responses, and leak terms.
- Export a minimal fresh-agent launch packet that excludes run records, rubric files, score output, workspace manifests, scenario JSON, and prior analysis.
- Verify the exported fresh-agent packet after copy/handoff for required files, forbidden files, manifest consistency, prompt hashes, and leak terms.
- Render a copy-paste fresh-agent launch prompt from the audited packet plus the allowed local skill root.
- Finalize fresh-agent run records with automatic scoring, response hashes, and an external human rubric before verification.
- Run a machine-readable pressure audit that emits hard questions, failure modes, accepted gaps, and next actions.
- Run a category coverage audit so major CTF route/reference/demo/forward/benchmark gaps stay visible.
- Run an evidence contract audit so writeups and handoffs cite EvidenceRecord entries, raw artifacts, contrast checks, and verification outcomes.
- Run a release consistency audit so manifest, version, validation, release gate, and traceability docs cannot drift silently.
- Validate `CTFRunState` integrity before benchmark verification and release gate.
- Evaluate phase gates before active testing, final report, or handoff.
- Render post-run reflection candidates from `CTFRunState`.
- Package validation, handoff, writeup, and reflection into one run artifact directory.
- Render deterministic checkpoints for context compression, pause/resume, and handoff prep.
- Add at least one refinement from real tool friction: `ctf_preflight.py` profile aliases.
- Produce one complete writeup from `ctf-handoff-report`.
- Run at least one real or benchmark CTF task and compare behavior against the synthetic demo baseline.

Still needed for a stricter externally verifiable v1:

- Run on at least one challenge per major category.
- Add at least one anti-injection rule from real suspicious content.
- Confirm installed skills trigger in the intended order in the target agent beyond deterministic metadata probes.
- Rerun the final fresh-agent packet in a clean context and preserve a verified 7/7 run record if strict certification is needed.

## Quality Gate

`scripts/audit_quality.py` turns the reflection audit into executable checks. It fails if the suite loses the requested reference-source absorption, weakens source matrix conversion evidence, lets SKILL.md files grow past the progressive-disclosure budget, drops a major deep-topic route, removes safe demo coverage, forgets reflection hard questions, removes the pressure audit accepted gap, weakens category coverage auditing, weakens the evidence contract, weakens release consistency auditing, checkpoint discipline, profile update coverage, phase-gate discipline, agent metadata validation, forward-test prompt integrity, forward-run initialization, forward-run rubric generation, answer-free fresh-agent handoff generation, fresh-agent readiness auditing, minimal fresh-agent packet export, exported packet verification, launch prompt rendering, forward-run finalization, completion auditing, weakens trigger/conflict audit coverage, weakens release validation, or falsely marks fresh-agent validation complete.
