# CTF State Schema

Use this schema to keep work resumable and auditable. Store state as JSON or Markdown with equivalent fields.
Validate JSON state with `scripts/validate_state.py` before handoff, writeup, benchmark verification, or resuming a long run.
Update `ChallengeProfile` fields with `scripts/update_profile.py` instead of manually editing JSON whenever possible.
Evaluate phase readiness with `scripts/gate_state.py` before active testing, solved claims, final reports, or handoff.
Render a resumable checkpoint with `scripts/checkpoint_state.py` before context compression, long pauses, or handoff prep.

## ChallengeProfile

Required fields:

- `title`: challenge name.
- `platform`: CTFd/event/local/lab/unknown.
- `category_claimed`: label from the platform, if any.
- `category_inferred`: agent's current category.
- `category_confidence`: `low`, `medium`, or `high`; use `low` for unverified platform labels.
- `description`: short sanitized description.
- `flag_format`: known format or `unknown`.
- `rules`: scan limits, AI/tool limits, submit limits, VPN/OOB notes.
- `targets`: URLs, hosts, ports, local services, Docker services.
- `attachments`: path, sha256, type, size, trust label.
- `credentials`: description only; do not store raw secrets unless user explicitly provided throwaway challenge credentials.
- `scope_status`: one of `unknown_needs_confirmation`, `local_only`, `authorized_remote`, `authorized_lab`, `benchmark_scope_pending`, or `local_authorized_benchmark`.

## CTFRunState

Required fields:

- `challenge`: `ChallengeProfile`.
- `environment`: tool and network preflight results.
- `evidence`: append-only `EvidenceRecord` list.
- `known_facts`: observed facts with evidence IDs.
- `hypotheses`: testable ideas with confidence and next experiment.
- `attempts`: chronological actions.
- `dead_ends`: excluded paths with proof.
- `artifacts`: raw outputs, screenshots, extracted files, scripts, dumps.
- `anti_injection_findings`: suspicious untrusted-content notes.
- `next_actions`: at most 5 prioritized actions.
- `handoff_ready`: boolean.

## EvidenceRecord

Required fields:

- `id`: stable short ID, e.g. `ev-001`.
- `timestamp`: ISO 8601.
- `actor`: agent/user/tool.
- `action`: command, browser action, code read, search, or manual observation.
- `purpose`: question being answered.
- `inputs`: sanitized inputs.
- `raw_artifact`: file path or URL to raw output.
- `summary`: concise result.
- `exit_status`: command exit code or observation status.
- `supports`: facts/hypotheses supported.
- `contradicts`: facts/hypotheses contradicted.
- `risk`: sensitive data, destructive risk, scope risk, or `none`.

## HandoffPacket

Required fields:

- `challenge_summary`
- `environment_summary`
- `current_state`
- `evidence_table`
- `attempts_and_dead_ends`
- `hypotheses`
- `most_likely_next_steps`
- `questions_for_human`
- `artifact_paths`
- `safety_notes`

## CheckpointPacket

`scripts/checkpoint_state.py` renders this derived, read-only packet from `CTFRunState`:

- `validation`: state validation status, errors, and warnings.
- `challenge`: compact scope/category/target/rule summary.
- `counts`: record counts by state section.
- `current_facts`, `active_hypotheses`, `recent_evidence`, `recent_attempts`, `dead_ends`, `next_actions`.
- `artifact_paths`: raw outputs and run directories to reopen only as needed.
- `resume_risks`: scope, validation, dead-end, evidence, next-action, and untrusted-content risks.
- `resume_checklist`: safe steps for another agent or future self to continue without rereading everything.
