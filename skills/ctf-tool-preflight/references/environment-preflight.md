# Environment Preflight

## Local

- OS and architecture.
- Python, Node, Go, Rust if source builds are needed.
- Disk space for extraction, pcaps, memory dumps, Docker images.
- Time synchronization for token/session/time-based crypto.
- Working directory for artifacts: `artifacts/raw`, `artifacts/summaries`, `artifacts/scripts`.

## Network

- Competition rules for scanning and automation.
- VPN connected if required.
- DNS resolution for challenge domains.
- Proxy configuration if required.
- Remote host/port reachable with safe probe.
- Rate limits and submit limits.

## OOB/VPS

- Authorized use confirmed.
- Domain/IP/ports prepared.
- Firewall/security group open only as needed.
- HTTP/DNS logs enabled.
- Temporary files isolated and cleaned after.

## GUI and Heavy Tools

- Browser profile isolated.
- IDA/Ghidra license and project directory ready.
- Emulator/VM snapshots available.
- GDB/pwndbg compatible with target architecture.
- Wireshark/tshark installed for pcaps.
