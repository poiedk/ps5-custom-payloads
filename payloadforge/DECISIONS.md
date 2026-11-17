# Decisions

- Keep existing PLDMGR IDs and URL; never publish from a development branch.
- Use opt-in archive policy and explicit exact member selection; do not infer installation paths from ZIP contents.
- SHA-256 verifies integrity, not author identity or binary safety.
- Hold unverified sources and packages with unknown redistribution permissions.
- Keep native build and hardware conclusions separate from host-side Python.
- Stage 2: prefer standard-library TAR.GZ; defer 7Z in v1 to avoid an additional parser/dependency and native-port complexity.

- Stage 4: use immutable managed generations and a single atomic CURRENT pointer, not in-place overwrites. Managed callers resolve the active generation. The root must be private; external application-specific layouts and executable companion files are not approved yet.
- Stage 5: dependency constraints are explicit AND comparisons over numeric semantic versions; no automatic fetching or silent upgrades. Unknown or incompatible constraints block an install.

- Stage 7–9: snapshots are retained, verified, and separate from the active generation; rollback preserves latest configs. Uninstall deactivates before cleanup and never deletes untracked files. Drop-config controls automatic reuse, not backup erasure.
- Stage 11: SDK v0.42 is pinned because its release notes explicitly add firmware 13.60 support. Pin checksum from CI and require it to match the official release metadata. Build a read-only smoke ELF, not a fake installer; no native mutation until full engine parity.
- Original PayloadForge code is intended as GPL-3.0-or-later, compatible with the SDK's GPL terms. COPYING applies to the payloadforge subproject, not a retroactive relicensing of third-party payloads; verify corresponding-source obligations before native distribution.
- Stages 12–13: host preview binds loopback only and uses an ephemeral bearer token; no LAN/external exposure, no automatic launch. Native daemon/UI remain dependent on a validated native engine.

- Native N1–N3: use bounded, ASCII-only data paths, strict JSON, stored ZIP only and independently verified archive/manifest hashes. Reject compression, nonempty dependency/resource/conflict arrays, executable companion paths and unknown syntax rather than silently weakening validation.
- Native N4: implement initial install only behind a private, pre-opened root directory descriptor. Use no-follow relative filesystem operations, exclusive lock, content-addressed staging and a single atomic CURRENT pointer. Retain interrupted staging for inspection; no recursive deletion. Native storage is not a migration of the Python host registry. Update/backup/rollback/uninstall parity is not yet present. Keep the exported ELF read-only until the native mutating entry point, parity and hardware gates are validated.
