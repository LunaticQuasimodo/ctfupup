# Benchmark Runbook

Use this runbook when proving `REQ-EVAL-REAL-CTF`. It is a gate for real evidence, not a substitute for running a challenge.

## Accepted Targets

- Cybench task or subtask running in an authorized local/evaluation environment.
- NYU CTF Bench dockerized task running locally.
- A legally downloadable CTF challenge with local artifacts and no live third-party target.
- An authorized lab challenge where rules explicitly allow AI-assisted solving.

## Initialize

```bash
python3 scripts/init_benchmark_run.py \
  --benchmark cybench \
  --challenge-id "<id>" \
  --title "<title>" \
  --category "<category>" \
  --source-url "<source>" \
  --out-dir /tmp/ctf-benchmark-run \
  --json
```

## Required Evidence

- `benchmark-profile.json` with benchmark version or source URL.
- `ctf-state.json` with scope, facts, hypotheses, evidence, dead ends, and next actions.
- Raw artifacts under `artifacts/raw/`.
- Handoff or writeup rendered from the state.
- Candidate flag derivation path.
- Validator/oracle/submission result proving whether the candidate is accepted.
- A short comparison against the synthetic baseline from `scripts/run_demo_solve.py --all`: routing, evidence quality, tool failures, and anti-injection handling.

## Not Enough

- A local synthetic fixture alone.
- A copied public writeup.
- A candidate flag without validator/oracle evidence.
- Tool output summarized without raw artifact paths.
- A solved claim without `CTFRunState`.
