# Pwn and Reverse Triage

## Binary Metadata

Run and save:

```bash
file ./chall
sha256sum ./chall
checksec ./chall || true
readelf -h ./chall
readelf -l ./chall | sed -n '1,120p'
strings -a ./chall | head -200
```

## Pwn Questions

- What is the protocol?
- Can local behavior reproduce remote behavior?
- What input controls length, format, index, pointer, size, path, or command?
- Is there a crash? If yes, is control over RIP/EIP/PC proven?
- What protections are enabled?
- What leak exists or can be created?
- What write/control primitive exists?
- What is the final objective: shell, read flag, function call, or ROP syscall?

## Reverse Questions

- Where does user input enter?
- Where is success/failure decided?
- Is the check linear, symbolic, cryptographic, VM-based, or obfuscated?
- Are constants/tables/xrefs meaningful?
- Can dynamic tracing confirm static assumptions?
- Can the solver be verified against the original binary?

## Evidence Patterns

| Claim | Required Evidence |
|---|---|
| Offset known | cyclic pattern result or debugger proof |
| Canary leak | leak output and stack position |
| Libc base known | leaked symbol and libc version |
| PIE base known | text pointer and offset calculation |
| Heap primitive | allocator state before/after |
| Reverse key recovered | derivation and binary accepts it |
| Constraint solver valid | constraints source and verification run |
