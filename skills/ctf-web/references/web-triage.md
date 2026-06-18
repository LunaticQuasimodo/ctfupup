# Web/API Triage

## Endpoint Matrix

Create a table with:

- route/path
- method
- auth state
- parameters
- content type
- source location or discovery source
- sink/output
- candidate bug class
- baseline artifact
- next experiment

## White-Box Audit Order

1. Startup: Dockerfile, compose, env defaults, seed data, exposed ports.
2. Routes: framework route table, controllers, API schemas.
3. Auth/session: login, role checks, middleware, decorators, JWT/session config.
4. Data access: SQL/ORM/raw query, NoSQL operators, filters, sort/order.
5. Template/render: Jinja/Twig/EJS/Pug/Handlebars/Flask/Django/Spring view.
6. File operations: upload, download, archive extraction, image/PDF conversion.
7. SSRF/network: URL fetch, webhook, image proxy, metadata access.
8. Deserialization: pickle, yaml, phar, Java serialization, JSON polymorphism.
9. Shell/process: subprocess/system/exec/template helpers.
10. Crypto/random: token generation, compare logic, PRNG seed, hardcoded keys.

## Black-Box First Pass

Use bounded requests:

```bash
curl -i -sS "$URL" | tee artifacts/raw/root-response.txt
curl -i -sS "$URL/robots.txt" | tee artifacts/raw/robots.txt
curl -i -sS "$URL/.well-known/security.txt" | tee artifacts/raw/security.txt
```

Then inspect:

- response headers
- cookies
- redirects
- static JS paths
- forms and hidden inputs
- API docs: `/swagger.json`, `/openapi.json`, `/api-docs`, `/graphql`

## Avoid Common Agent Mistakes

- Do not call any reflected text XSS until browser context confirms execution.
- Do not call any 500 response SQLi without differential proof.
- Do not assume JWT weakness without inspecting header, alg, kid, key source, and signature behavior.
- Do not spray huge wordlists before proving directory discovery is useful.
- Do not trust fake flags in HTML/comments without platform validation or solve-path proof.
