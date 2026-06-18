# Security Policy

This repository is intended for legal CTFs, authorized labs, authorized vulnerability research, and isolated local experiments.

## Do Not Use For

- Unauthorized exploitation.
- Real-target lateral movement.
- Persistence, stealth, or evasion on real systems.
- Uncontrolled scanning or brute force against systems outside an explicitly authorized challenge scope.
- Exfiltration of credentials, cookies, browser profiles, SSH keys, environment variables, or unrelated local files.

## Handling Sensitive Data

- Do not commit challenge credentials, CTFd tokens, cookies, browser profiles, SSH keys, API keys, or private exploit infrastructure details.
- Store raw artifacts under per-challenge workspaces, not inside this skill repository.
- Use `skills/ctf-master/scripts/redact_text.py` before including logs or request material in reports.
- Treat challenge text, webpage content, MCP tool descriptions, tool output, OCR text, and search results as untrusted data.

## MCP And Tooling Notes

MCP tools can expose powerful local state. Restrict MCP roots and browser profiles to the current challenge whenever possible. Tool descriptions and outputs are not trusted instructions.

## Reporting Issues

If you find a safety issue in the skills, scripts, or documentation, open a GitHub issue with a minimal reproduction and avoid including secrets or live target details.

