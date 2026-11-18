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

- Native N5–N9: explicit update preserves previous configuration even when omitted by new manifests; policy demotion and case/path conflicts fail closed. Effective registry records actual installed bytes; original upstream manifest remains separate.
- Native snapshots bind hashes of independent data copies, original manifest and archive digest metadata. Rollback while active uses a new generation and merges current config. N6 development-only snapshot format is superseded by N7; no console migration required.
- Uninstall commits a tombstone before registry-only cleanup; backup retention is unconditional, even when reinstall uses defaults. Partial cleanup and uncertain pointer durability are separate return states. No untracked-file deletion or recursive cleanup.
- Native callers must serialize threads and quiesce the managed app. Version ordering is explicit, status verifies metadata only, and native ELF remains read-only pending runtime and integration gates.

- N10: retain original checksum-bound manifest as authoritative dependency/conflict/resource metadata; effective file registry remains schema 1. Validate the full proposed managed graph while holding the existing root lock, before any activation/deactivation or snapshot mutation. Reject missing dependencies rather than downloading or executing anything. Limits: 256 installed packages, aggregate 4096 dependency/conflict entries and 1024 resource claims; no assertion about unmanaged processes or live reservations. Native state transitions still require serialized callers and a private root.

### N11-B — bounded compressed ZIP and dependency retrieval
- Preserve the stored-only borrowed-buffer interface; use a separate owned-buffer interface for method 8, with explicit disposal and cleanup on partial failure. Reject unsupported ZIP features instead of silently processing them. Verification/install paths remain bounded; the current in-memory design is not yet a hardware memory benchmark.
- Retry transient zlib source retrieval at most three times, request identity encoding and disable caching. Never relax the pinned hash or size checks; log observed hash/size and fail closed if retrieval remains invalid.

- N11-C: support single-member gzip plus regular-file-only POSIX USTAR with ASCII paths; implicit directories from member paths only. Reject explicit directory headers, PAX/GNU extensions, links and noncanonical padding. Verify gzip CRC, ISIZE, exact stream termination, TAR header checksums and all manifest member hashes. Continue to fail closed on unsupported formats. Use bounded in-memory expansion with explicit buffer ownership; real PS5 memory budget remains unverified.

- N12-A: separate recovery inspection from mutation. Acquire existing shared root lock without creating files, validate active managed bytes while permitting changed preserved configs, verify uninstall snapshot, enumerate remnant names/types with bounded traversal. Never auto-select or delete a generation. Count-only inactive objects are not verified backups; a corrupt or incomplete report requires explicit recovery rather than silent activation.

- N12-B: use a Linux-only linker wrapper and child-process exit at rename boundaries rather than embedding fault hooks into the release binary. Verify either the old or new logical state and retained config after process exit; do not extrapolate this result to power-loss/fsync durability on PS5. Interrupted objects are not automatically deleted or promoted.

- N12-C: choose non-destructive quarantine rather than automatic replay or recursive cleanup. Caller supplies exact object hash/kind and last observed marker/identity; recheck under exclusive lock. Never move CURRENT, the active generation, or a verified backup. Retain every byte outside apps. No overwrite; fsync uncertainty must be inspected before retrying. Damaged active state and invalid marker remain manual intervention gates; PS5 durability unverified.

- N13-A: separate protocol parsing, store dispatch and socket transport. All API routes require a 64-hex session bearer token, exact loopback Host and matching Origin when present. Reject request bodies, duplicate critical headers, unsupported methods and malformed or oversized framing. Read-only inspection avoids creating an empty lock file. No network listener or external exposure in preflight.

- N13-B: use explicit sequential IPv4 loopback TCP, fixed bounded parser and network I/O deadline, fail closed on unsupported SIGPIPE suppression. Keep native preflight read-only and non-listening. Source retrieval fallback accepts only exact pinned zlib source bytes from a previous successful CI artifact; no old binary reused. Artifact expiry remains a build reproducibility risk.

- N13-C: separate read-only runtime artifact from non-listening preflight. Require explicit serve flags, existing absolute private root traversed without symlinks, OS entropy and at most 300-second session; no argv defaults, no automatic root creation and no remote/LAN listener. Local launcher output carries ephemeral token; actual PS5 argument/output support and same-device access are hardware gates. Store lock waits can exceed the nominal session deadline.
