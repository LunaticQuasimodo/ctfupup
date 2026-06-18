# Specialty Triage

## Blockchain

- Framework: Foundry, Hardhat, Truffle, raw web3.
- Inputs: contracts, ABI, bytecode, deployment scripts, RPC, wallet/key, challenge address.
- First commands: run tests, inspect balances, call read-only methods, trace failing exploit.
- Evidence: tx hash, event logs, state diff, invariant/profit/flag condition.

## AI/LLM Security

- Assets: prompt boundary, RAG corpus, tools, memory, browser, file/network permissions.
- Tests: direct injection, indirect injection, tool argument injection, context leakage, fake source poisoning.
- Evidence: exact prompt, retrieved snippet, tool call args, output, success condition.
- Safety: never exfiltrate real secrets; use challenge-provided canaries only.

## Mobile

- APK/IPA metadata, manifest/plist, exported components, deep links, network config.
- Decompile and search for endpoints, secrets, crypto, native libs, debug/root/pinning checks.
- Route backend API to Web; route native library checks to Pwn/Reverse.

## IoT

- Firmware file type, binwalk, filesystem, architecture, init scripts, web service, hardcoded creds.
- Check update signatures and config defaults.
- Emulate only with isolation and architecture support.

## Cloud/K8s/Container

- Manifests, IAM policies, service account tokens, metadata endpoints, storage buckets, signed URLs.
- Container: capabilities, mounts, namespace, Docker socket, privileged mode.
- K8s: RBAC, secrets, kubelet, service account token audience and permissions.
- Evidence should be minimal and read-only unless rules explicitly permit changes.
