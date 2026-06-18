---
name: ctf-web
description: Web and API CTF challenge workflow. Use for CTF tasks involving HTTP services, source web apps, REST/GraphQL APIs, login/session/cookie issues, SSRF, SQLi, SSTI, XSS, file upload/download, path traversal, deserialization, command injection, browser automation, JavaScript endpoint discovery, or CTF web black-box/white-box triage.
---

# CTF Web Skill

Use this after `ctf-master` routes a challenge to Web/API. Keep testing legal, rate-limited, and scoped to the challenge target.

## Intake

Record:

- URL/host/port, protocol, VPN/proxy need, credentials, flag format.
- App stack evidence: headers, cookies, framework files, source tree, Dockerfile, routes.
- Auth state: anonymous, user, admin, provided account, synthetic local account.
- Allowed automation and scan limits from the competition rules.

## White-Box Path

1. Read route definitions, controllers/handlers, middleware, auth/session code, serializers, templates, DB access, file operations, subprocess calls, crypto/randomness, Docker startup.
2. Build an entrypoint table: route, method, auth requirement, parameters, sink, output, candidate bug class.
3. Prioritize paths where user input reaches an interpreter, file path, template, SQL/NoSQL, shell, deserializer, SSRF client, JWT/session verifier, or permission check.
4. Design one minimal experiment per hypothesis. Do not fuzz before understanding request shape.

## Black-Box Path

1. Fingerprint with safe requests: `curl -i`, browser snapshot, robots/sitemap, JS list, common API docs, visible forms.
2. Build an endpoint/parameter matrix before payloads.
3. Establish baseline requests and compare against modified requests.
4. Use browser automation only when DOM state, cookies, localStorage, JS routing, or visual interaction matters.
5. Keep scans bounded: prefer focused `ffuf`/`feroxbuster` lists over broad recursive brute force.

## Vulnerability Routing

| Signal | Focus |
|---|---|
| ID/user/object in URL/JSON/header | BOLA/IDOR, authz bypass, mass assignment |
| Template syntax, render errors, Flask/Jinja/Twig/EJS | SSTI |
| SQL errors, search/filter/sort, unusual timing | SQLi/NoSQLi |
| URL fetch, webhook, image import, PDF render | SSRF |
| File path/download/include/export | Path traversal/LFI/RFI |
| Upload + parser/static hosting | Upload bypass/polyglot/content-type |
| Cookie/JWT/session/remember-me | Token trust, weak signature, alg/key confusion |
| YAML/XML/PHP/Java/Python object input | Deserialization/XXE |
| Command wrappers, image/video/archive processors | Command injection |
| Reflected/stored HTML/JS, admin bot | XSS/CSP/browser challenge |

## Evidence

Every claim needs:

- Baseline request.
- Modified request.
- Response difference.
- Side effect or extracted value.
- Raw artifact path.

For blind/OOB cases, record callback domain, timestamp, request ID, source IP if visible, and exact payload. Avoid destructive payloads and data dumping.

## References

Read when needed:

- `references/web-triage.md`: endpoint matrix and source audit checklist.
- `references/browser-workflow.md`: browser/DevTools workflow and screenshots.
- `../ctf-master/references/acceptance-gates.md`: before declaring solved or excluded.
