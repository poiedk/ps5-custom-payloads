# PayloadForge progress

All development is isolated from `main`. No stable release or console execution.
Statuses distinguish implemented, CI-verified and hardware-verified.

## Stage 0 — baseline/security
- CI verified: [run 44161036271](https://github.com/poiedk/ps5-custom-payloads/actions/runs/44161036271), commit 332847c.
- Actual log: `Ran 35 tests in 0.009s` / `OK`.
- Hardware: not tested.

## Stage 1 — ZIP updater
- CI verified: [run 44161758677](https://github.com/poiedk/ps5-custom-payloads/actions/runs/44161758677), commit da1ae8c.
- Actual log: `Ran 45 tests in 0.020s` / `OK`.
- No live archive source enabled; redistribution/compatibility need review.
- Hardware: not tested.

## Stage 2 — TAR.GZ reader
- CI verified: [run 44162680414](https://github.com/poiedk/ps5-custom-payloads/actions/runs/44162680414), commit 57b857b.
- Actual log: `Ran 57 tests in 0.024s` / `OK`.
- Bounded gzip decompression, exact ELF selection, special-file and path rejection, limits and documentation-only policy.
- 7Z deferred; additional parser dependency and native-port risk outweigh benefit for v1.
- TAR integration with updater/content detector to follow in Stage 3; no live TAR source.

## Stage 3 — content detection and TAR routing
- CI verified: [run 44163136536](https://github.com/poiedk/ps5-custom-payloads/actions/runs/44163136536), commit 5989f1c.
- Actual log: `Ran 70 tests in 0.034s` / `OK`.
- Detect ELF, ZIP, TAR.GZ and root manifest marker from bytes; classification is not integrity verification.
- TAR.GZ integrated into opt-in updater; mismatched content and manifest bundles rejected from standalone publishing.
- Host-only fixtures; no live source or hardware test.

## Stage 4 — host transaction engine
- CI verified: [run 44163735332](https://github.com/poiedk/ps5-custom-payloads/actions/runs/44163735332), commit ad7ad5a.
- Actual log: `Ran 80 tests in 0.103s` / `OK`.
- External-manifest data-only ZIP install/update into a private managed root; atomic CURRENT pointer and registry, SHA-256, configuration preservation, failed pre-activation cleanup.
- Host only: not a native installer; no arbitrary application/system paths. Power-loss durability on PS5 is unverified.

## Stage 5 — dependency validation
- CI verified: [run 44164226104](https://github.com/poiedk/ps5-custom-payloads/actions/runs/44164226104), commit b670338.
- Actual log: `Ran 90 tests in 0.118s` / `OK`.
- Version comparisons, topological order, missing/cyclic dependencies, reverse-dependent upgrade checks. Schema v1 remains accepted; v2 adds dependencies. No automatic download or execution.

## Catalog review (independent work)
- CI verified: [run 44164420759](https://github.com/poiedk/ps5-custom-payloads/actions/runs/44164420759), commit 8fc3518.
- Actual log: `Ran 102 tests in 0.097s` / `OK`.
- Offline candidate guard checks canonical source, publisher, repo age, pinned source evidence, independently supplied artifact bytes/hash, compatibility, review evidence and duplicate IDs/names/origins. It does not prove malware safety.
- Reviewed 12 named projects against the official 34-entry mirror and current sources; WebKit, ShadowMountPlus and Linux loader are official duplicates, HearBridge already custom. Others remain held; no new source was promoted.
- Automation read returned action-not-found; existing discovery task was not modified. Requirements documented for future discovery.

## Stage 6 — conflict detection
- CI verified: [run 44164854065](https://github.com/poiedk/ps5-custom-payloads/actions/runs/44164854065), commit f7336bcd.
- Actual log: `Ran 111 tests in 0.096s` / `OK`.
- Schema v3 adds explicitly declared TCP/UDP ports, path claims and incompatible version ranges. Reverse conflicts checked before mutation. Does not inspect unmanaged live processes.

## Stage 7 — verified backups
- CI verified: [run 44165241636](https://github.com/poiedk/ps5-custom-payloads/actions/runs/44165241636), commit 0a77dd4.
- Actual log: `Ran 117 tests in 0.208s` / `OK`.
- Pre-update snapshot of all registered files and actual current config hashes; first install has no previous data. Manual backup, listing, tamper detection. Failed backup blocks update. Host only; snapshots retained.

## Stage 8 — rollback and recovery
- CI verified: [run 44165529848](https://github.com/poiedk/ps5-custom-payloads/actions/runs/44165529848), commit 43506ca.
- Actual log: `Ran 123 tests in 0.139s` / `OK`.
- Verified snapshot restore; preserve latest configs, validate dependency/conflict graph, backup before restore. Simulated faults before/after pointer switch, including initial install. Recovery report is read-only.
- This is exception/fault injection on host, not physical power interruption or PS5 testing.

## Stage 9 — registry-only uninstall
- CI verified: [run 44165913002](https://github.com/poiedk/ps5-custom-payloads/actions/runs/44165913002), commit 1df8eb4.
- Actual log: `Ran 129 tests in 1.014s` / `OK`.
- Atomic uninstall marker, verified snapshot, cleanup of registry-listed files in inactive generation only, untracked files retained. Optional config reuse on reinstall; backups remain intact even with drop-config.
- Reverse dependencies block removal. Cleanup failure is reported, not hidden.

## Stage 10 — version management and host CLI
- CI verified: [run 44166289938](https://github.com/poiedk/ps5-custom-payloads/actions/runs/44166289938), commit e03ebea.
- Actual log: `Ran 135 tests in 0.440s` / `OK`.
- Explicit install/upgrade/downgrade direction, list/info/backups/versions/rollback/uninstall/recovery; strict JSON and confirmation for writes. No payload execution.
- Host CLI only, not PS5-native; no runtime package download.

## Stage 11 — native port (partial)
- First CI run [44166891431](https://github.com/poiedk/ps5-custom-payloads/actions/runs/44166891431): host `Ran 139 tests in 0.404s` / `OK`; native build failed with llvm-config path Error 127.
- Retry [44167128569](https://github.com/poiedk/ps5-custom-payloads/actions/runs/44167128569), commit 8943fd7: both jobs succeeded. Actual host log `Ran 139 tests in 2.040s` / `OK`; `PayloadForge native preflight: OK (read-only; not installer)`.
- SDK v0.42 pinned SHA-256: 8cfbc7cd5811e719eb4f0c47eea668d3dc7b40bc8ab11c4a5031d40c23ec02da.
- CI emitted read-only cross-compiled `payloadforge-preflight.elf`, SHA-256 10f652db2aa064374ff08b2c468dc31c90d27b7087871f664fa0ca15fb8038d7, artifact 14366007046. No execution/deployment.
- C path/id/hash syntax and format-magic vectors verified on host. Full archive/manifest parser, cryptographic hashing and transactional engine parity in C are **not** implemented. Native installation remains blocked; no claim of console functionality.

## Stage 12 — host-only API
- CI verified: [run 44167528195](https://github.com/poiedk/ps5-custom-payloads/actions/runs/44167528195), commit ca2f009.
- Actual log: `Ran 148 tests in 7.210s` / `OK`. Native read-only preflight also cross-compiled successfully.
- Loopback-only authenticated JSON API, explicit confirmation, host/origin checks, size limits, logs, synthetic data-bundle transactions. Independent host work; native PS5 daemon not implemented.

## Stage 13 — host-only web interface
- CI verified: [run 44168094580](https://github.com/poiedk/ps5-custom-payloads/actions/runs/44168094580), commit 5b20a22.
- Actual log: `Ran 150 tests in 5.838s` / `OK`; native preflight host smoke OK and ELF cross-compile successful.
- Host UI covers package list, preview/apply, version management, backups, rollback, uninstall, recovery and logs. Static delivery and JS syntax tested; full browser E2E and native UI unverified.

## Stage 14 — companion catalog
- CI verified: [run 44168437654](https://github.com/poiedk/ps5-custom-payloads/actions/runs/44168437654), commit ea4ecb8.
- Actual log: `Ran 160 tests in 5.605s` / `OK`. Both jobs passed.
- Separate empty sidecar and read-only CLI join; actual catalog regression confirms no changed IDs. Native integration not implemented.
- Discovery automation was successfully retrieved via peek and updated to staged review/green-CI policy; schedule unchanged. No unverified source added.

## Stages 15–16 — planned hardware gate and host preview
- HUMAN_TODO.md contains the hardware test plan; no PS5 test executed.
- RC.md describes 0.1.0-alpha host preview and separate read-only native preflight. No full installer RC or stable release.
- Final host-preview CI verified: [run 44169115873](https://github.com/poiedk/ps5-custom-payloads/actions/runs/44169115873), tested commit dde33dd. All three jobs completed successfully.
- Actual log: `Ran 162 tests in 5.814s` / `OK`; `PayloadForge native preflight: OK (read-only; not installer)`.
- Host alpha artifact 14366697030, source TAR.GZ SHA-256: 58342ef8f33c726812b4bb819ac1001527c491a7df6e2dd5bec97de59db3bcc8.
- Native read-only preflight artifact 14367276278, ELF SHA-256: 10f652db2aa064374ff08b2c468dc31c90d27b7087871f664fa0ca15fb8038d7.
- Production verified unchanged: sources.json 37041fd, update.py 8d6bc48, status.json d4c93e8, nine payload IDs. OmniPad/LZ4 warnings remain. No merge, stable release or hardware operation.
- Autonomous run ends with a verified host alpha and native smoke build, not a functional PS5 installer. Full native port and its dependent PS5 web/catalog integration remain engineering work, not simply hardware approval.

## v0.2 native phase — N1: SHA-256
- CI verified: [run 44176203350](https://github.com/poiedk/ps5-custom-payloads/actions/runs/44176203350), commit 328aed3. All three jobs passed.
- Actual log: `Ran 166 tests in 8.928s` / `OK`. Native preflight cross-compiled; SHA-256 b25ba61f4e7062787455a39c448f6f3532313c9e9263417464877da29ee6d10e.
- Portable SHA-256 compared with Python hashlib known, boundary and random byte vectors; no console execution.
## N2: strict native ZIP reader
- CI verified: [run 44176662095](https://github.com/poiedk/ps5-custom-payloads/actions/runs/44176662095), commit 548fe48. All three jobs passed.
- Actual log: `Ran 177 tests in 6.181s` / `OK`.
- ZIP_STORED, ASCII paths, standard 32-bit, contiguous entries only. No compression, ZIP64, extra fields, explicit dirs, symlinks or special files. CRC and duplicate/prefix checks. No filesystem writes.
- Native DEFLATE/TAR.GZ remain unimplemented; host updater retains broader support.

## N3: native manifest and read-only bundle verifier
- CI verified: [run 44177098894](https://github.com/poiedk/ps5-custom-payloads/actions/runs/44177098894), commit eb2f797. All three jobs passed.
- Actual log: `Ran 189 tests in 5.973s` / `OK`; native smoke build succeeded, artifact 14370212500, ELF SHA-256 70ff99672b240d2fc914fad2370092cb54ca1c1ebc79867967cb73d8941c8b81.
- Strict ASCII JSON subset, schemas 1–3 with empty dependencies/resources/conflicts only. Invalid keys, duplicates, path overlap and executable companions rejected. Independently supplied archive and manifest SHA-256 plus exact member size/hash.
- No file writes. Nonempty constraints and compressed archives fail closed until native support exists.

## N4: native initial-install store
- Initial run 44177616907: host `Ran 197 tests in 7.089s` / `OK`; SDK cross-compile failed for flock/sys/file.h.
- Retry [44177784467](https://github.com/poiedk/ps5-custom-payloads/actions/runs/44177784467), commit 4ace69a: host tests and native preflight compilation succeeded.
- Actual log: `Ran 197 tests in 8.531s` / `OK`; `PayloadForge native preflight: OK (read-only; not installer)`.
- ELF SHA-256 6bfef88e75cf97cba5c0875627c00f6bc1374b8566aedec59ec7a207ad889572; artifact 14369274154.
- Initial-install-only library is linked; writes exercised in Linux host tests, not on PS5. Private directory fd, POSIX process lock, no symlink following, verified data-only ZIP, staging, fsync and atomic CURRENT pointer. Concurrent threads must be serialized by a future daemon; failure before activation may leave inactive staging/generation metadata for inspection.
- Update/config merge, registry parity, backup/rollback/uninstall, compressed archives, dependency metadata, native daemon and hardware validation still open.

## N5: native update and effective configuration registry
- Attempt 1: run 44179758605, overlapping helper definitions caused host and SDK compilation failures.
- Attempt 2: run 44179935698, SDK build passed but two existing regression assertions failed (omitted preserved configuration policy and predecessor-bound staging identity).
- Corrected implementation and reconciled tests with host policy: preserve omitted configurations; simulate pointer failure using actual generation identity.
- [Run 44180101366](https://github.com/poiedk/ps5-custom-payloads/actions/runs/44180101366), commit 9fad721: host `Ran 215 tests in 8.651s` / `OK`; native preflight compilation passed.
- Native update retains prior generation, validates upstream and effective registry hashes, verifies immutable prior data, copies current preserved files, rejects symlinks/hardlinks and conflicts. Same-version update rejected; version ordering and verified backup/rollback are separate gates. Native library only, no hardware execution.

## N6: native independent backups
- [Run 44180511787](https://github.com/poiedk/ps5-custom-payloads/actions/runs/44180511787), commit 713dc23. Host `Ran 222 tests in 12.498s` / `OK`; SDK native preflight compiled.
- Independent, content-addressed snapshots of registered data with actual byte hashes (including mutable configs). Manual backup and verification APIs, automatic pre-update snapshot, idempotent reuse only after verifying existing snapshot. Corrupt snapshots block updates.
- Caller must serialize threads and quiesce the managed app. Backup is linked in native library but not invoked by the read-only PS5 ELF. Hardware not tested.

## N7: native rollback with self-contained snapshots
- [Run 44181080867](https://github.com/poiedk/ps5-custom-payloads/actions/runs/44181080867), commit fa79fe0. Host `Ran 229 tests in 8.826s` / `OK`; SDK cross-compile succeeded, ELF SHA-256 38778e54a5933ba90bfc18b16e4b91b820b5bad07bba66c2f2d046b57f9770e8.
- Snapshots now bind the original upstream manifest and archive hash metadata as well as actual data and registry. Development-only older snapshot format is rejected; no console migration required.
- Rollback verifies snapshot independently of the old generation, backs up current state, merges latest preserved config, and atomically activates a fresh generation. Simulated failure before activation retains current marker. Physical power-loss and PS5 operation remain untested.
