---
name: ctf-pwn-rev
description: Pwn and reverse engineering CTF workflow. Use for ELF/PE/Mach-O/APK/JAR/native binaries, remote nc services, libc/ld bundles, core dumps, exploit development, checksec, stack/heap/format-string/ROP, GDB/pwndbg, angr/z3, IDA/Ghidra/radare2, packed binaries, VM bytecode, license/keygen, and static/dynamic reverse triage.
---

# CTF Pwn and Reverse Skill

Use this after `ctf-master` routes a challenge to Pwn or Reverse. Keep exploit attempts inside the provided binary/service and authorized challenge endpoint.

## Shared Triage

1. Hash and identify all binaries: `file`, `sha256sum`, architecture, endian, linkage, stripped status.
2. Record execution context: local binary, remote host/port, libc/ld, Dockerfile, seccomp, QEMU/architecture needs.
3. Run only safe metadata first: `checksec`, `strings`, `readelf`, `objdump`, import/export list.
4. Save raw outputs before summarizing.

## Pwn Workflow

1. Confirm I/O protocol manually or with a tiny pwntools harness.
2. Reproduce crash locally before remote exploitation when possible.
3. Determine primitive: overflow, format string, UAF, double free, OOB, integer bug, race, sandbox escape.
4. Establish proof: offset, canary/libc/PIE leak, write primitive, control-flow hijack, shell/read flag path.
5. Prefer minimal exploit script with clear stages and comments for non-obvious constraints.
6. Verify locally and remotely; record command, output, and final flag extraction method.

## Reverse Workflow

1. Locate input validation path: main, parser, dispatch table, crypto checks, VM loop, anti-debug, packer.
2. Use static analysis for structure, dynamic analysis for confirmation.
3. Name functions and variables as hypotheses until confirmed by behavior.
4. Extract constants, tables, transforms, encodings, and comparison points.
5. Use z3/angr/sage only when the constraints are identified and bounded.
6. Verify candidate flag/key by running the binary or reimplementing the check.

## Tool Routing

| Evidence | Tool |
|---|---|
| ELF protections, libc leak, ROP | checksec, pwntools, ROPgadget/ropper, gdb/pwndbg |
| Heap allocator behavior | glibc version, pwndbg heap, how2heap references |
| Format string | pwntools fmtstr, stack probes, leak table |
| Complex branch constraints | angr/z3 after manual boundary extraction |
| GUI reverse needed | IDA/Ghidra/radare2; use MCP only with trusted local project |
| Android/mobile native | apktool/jadx/frida only in isolated test device/emulator |
| Packed/obfuscated | detect packer, snapshot, dynamic trace, unpack before deep decompile |

## Evidence Gates

Do not claim success without:

- Crash/control proof or validation bypass proof.
- Exact binary/libc/remote version context.
- Reproducible exploit or solver script.
- Raw terminal output showing the flag or validated key.

## References

Read when needed:

- `references/pwn-rev-triage.md`: metadata, crash, exploit, and reverse checklists.
- `references/exploit-script-template.py`: minimal pwntools/solver structure.
- `../ctf-tool-preflight/references/tool-cards.md`: tool preflight expectations.
