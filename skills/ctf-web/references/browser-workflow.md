# Browser and DevTools Workflow

Use browser tooling when server responses depend on JavaScript, DOM state, localStorage, cookies, service workers, websockets, or visual interaction.

## Browser Evidence

Capture:

- current URL
- screenshot path
- DOM snapshot or relevant HTML
- cookies/localStorage/sessionStorage keys, with secrets masked
- network request/response for the tested action
- console errors

## Workflow

1. Open the challenge in an isolated browser profile.
2. Snapshot visible state before interaction.
3. Record network requests for login, API calls, upload/download, websocket, admin bot.
4. Reproduce key requests with curl or a script when possible.
5. Save screenshots only for evidence; do not rely on visuals alone for proof.

## Browser-Specific Attack Signals

- Admin bot challenge: stored XSS, CSP, same-site cookies, URL delivery.
- DOM challenge: source/sink in client JS, hash/query parsing, postMessage.
- WebSocket: auth token in URL/header, message schema, state transitions.
- Service worker/cache: stale assets, cache poisoning/deception, offline data.
- LocalStorage: JWT/session tokens, feature flags, role markers.
