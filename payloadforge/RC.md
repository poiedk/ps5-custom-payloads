# PayloadForge 0.1.0-alpha — host preview candidate

Release channel: CI artifact only (not stable, not a GitHub release).

- Host source preview includes the engine, CLI, authenticated loopback UI, tests and synthetic fixtures.
- Separate PS5 read-only preflight artifact is built with pinned SDK v0.42. It is not an installer and must never be added to autoload.
- A green host/native-smoke CI does not certify a working native installation engine.
- The full native installer RC is blocked on C/C++ parity (archive/manifest integrity, dependency/conflict validation, safe POSIX generation transactions, backups/rollback/uninstall), reviewed app-owned target mappings, native local daemon/UI, and native build/integration tests.
- Hardware plan is in HUMAN_TODO.md; no stable release or merge to main until the actual native RC and hardware results meet the release gate.

SDK upstream source: https://github.com/ps5-payload-dev/sdk/tree/v0.42
SDK artifact SHA-256: 8cfbc7cd5811e719eb4f0c47eea668d3dc7b40bc8ab11c4a5031d40c23ec02da
Original PayloadForge sources: this branch and COPYING. Review corresponding-source and third-party licenses before any public installer distribution.
