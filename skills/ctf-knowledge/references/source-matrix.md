# Source Matrix

Use this matrix for every external source that materially affects the solve or a skill update.

## Fields

- `source_name`
- `url_or_path`
- `source_type`: official docs, paper, benchmark, GitHub, tool README, writeup, blog, issue, personal note
- `topic`
- `relevance`: low/medium/high
- `core_claim`
- `borrowable_design`
- `do_not_blindly_copy`
- `skill_conversion`
- `credibility`: low/medium/high
- `freshness`: current/stale/unknown
- `local_verification_needed`

## Scoring

High credibility:

- official docs
- maintained tool docs
- benchmark papers with reproducible artifacts
- writeups with commands and files

Medium credibility:

- popular GitHub repositories without tests
- blog posts with reproducible commands
- CTF notes matching the exact primitive

Low credibility:

- snippets without context
- copied payload lists
- forum claims without reproduction

## Output Rule

A source should change the next action only if it produces a local check, not just a confident-sounding claim.
