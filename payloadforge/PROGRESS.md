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

## N8: native uninstall and reinstall
- [Run 44181579359](https://github.com/poiedk/ps5-custom-payloads/actions/runs/44181579359), commit f55a4ef. Host `Ran 236 tests in 8.816s` / `OK`; native preflight cross-compile succeeded.
- Verified backup followed by atomic deactivation marker. Cleanup only registry-listed regular, owner-owned single-link files; untracked files retained. Explicit config reuse or fresh defaults on reinstall; backups remain in both modes. Partial cleanup is reported.
- Reinstall uses fresh identity and optional verified snapshot. Rollback while uninstalled and cleanup recovery after abrupt interruption still open. No PS5 execution.

## N9: native version ordering and status
- Initial run 44182087063 passed but collected nine imported update tests twice. Changed test import to avoid duplicate collection.
- [Run 44182253046](https://github.com/poiedk/ps5-custom-payloads/actions/runs/44182253046), commit 9e6622f. Actual host output: `Ran 242 tests in 9.822s` / `OK`; native preflight compiled. ELF SHA-256 3dffce53f2a85418a3e096f0bae59f581c10e7eecc095d5973b32813b717b258, artifact 14373091894.
- Explicit upgrade/downgrade checks compare numeric components, prerelease and build metadata; Python cross-language vectors. Unknown version formats fail closed for ordered transitions; explicit generic update remains separate. Status reads verified registry metadata, not full data hashes.
- Native N1–N9 implemented in C for strict data-only stored ZIP subset. Outstanding: native nonempty dependency/conflict metadata, compressed archives, recovery of interrupted staging/cleanup and rollback while uninstalled, executable runtime/harness, daemon/UI and live-catalog integration, approved app-owned mappings and hardware validation. No installer RC or console execution.

## N10: native dependency and resource validator (partial)
- Added `native/constraints.c`, `native/constraints.h` and 9 tests in `test_native_constraints.py`.
- Validates an explicitly provided final package-state graph, including reverse dependency constraints, missing dependencies, cycles, declared version conflicts, TCP/UDP collisions and case-insensitive overlapping /data path claims.
- Limits: 256 packages, 64 dependencies/conflicts per list, 128 resource claims per package, aggregate 4096 dependency/conflict entries and 1024 resource claims.
- Linked the module into the native preflight build and included corresponding sources in the CI artifact configuration (commit 5352243).
- CI lookup did not return a run for 5352243 at the time of this entry. No N10 PASS claimed. Last verified complete run remains 44182253046 (242 tests).
- Manifest parsing and store operations still reject nonempty constraints; integration and persistence of dependency/resource metadata are the next gate, after validating this module.
- No changes to production or PS5.

### N10-A — validator verification
- [Run 44245013206](https://github.com/poiedk/ps5-custom-payloads/actions/runs/44245013206), commit 72f8332: all three jobs succeeded. Actual host log: `Ran 254 tests in 10.767s` / `OK`; `PayloadForge native preflight: OK (read-only; not installer)`.
- 12 native graph tests (including three additional bound/chain tests), native smoke assertions and SDK cross-compile verified. Read-only ELF SHA-256 72ae3a0c88d4675c1dad5cfe91408c8b33f0ec9282dae9f0f55bb772494cf6f7, artifact 14400553778.
- PR #3 merged into development ONLY at c5e7b93 after all three jobs passed. No merge to main. Manifest and store integration remains a separate gate.

### N10-B — strict manifest metadata and bundle verification
- [Run 44259990231](https://github.com/poiedk/ps5-custom-payloads/actions/runs/44259990231), commit 4bd89a7: all three jobs succeeded. Actual host log: `Ran 265 tests in 12.781s` / `OK`; native read-only preflight passed cross-compilation.
- 11 new tests cover metadata parsing, schema bounds, duplicates, malformed paths/constraints, graph validation and verifying exact archive+manifest+member bytes. Legacy mutation entry points still reject nonempty metadata.
- PR #4 merged into development ONLY at 14c09b3. ELF artifact 14407717435, SHA-256 173ae36ff92ff9c21a132c4fd707419ce058c42e7ef9f66a448c2f5653ab30e1.
- No PS5 write/execution. Next gate: atomically validate proposed whole managed state for install/update/rollback/uninstall, under store lock.

### N10-C — managed store dependency and conflict enforcement
- [Run 44260487683](https://github.com/poiedk/ps5-custom-payloads/actions/runs/44260487683), commit 53d3545: all three jobs succeeded. Actual host log: `Ran 274 tests in 12.475s` / `OK`; native host smoke passed and SDK cross-compiled read-only ELF.
- Nine new state-transition tests; verifies proposed final graph under root lock before install/update/rollback/uninstall. Blocks reverse dependency violations, cycles, declared path/port/version conflicts and corrupt peer manifests. Original hash-verified manifest is the canonical metadata source, including for restored snapshots; effective registry still records actual files and preserved config.
- PR #5 merged into development ONLY at 99ed31b. ELF artifact 14407857895, SHA-256 082651e3fdb72844ced2fdcdbd6ffa2c1d8206c779b685d3bb39c133ae50b552.
- Scope: managed, declared resources only; no probing unmanaged processes, no automatic dependency downloads or execution. Native runtime/hardware untested. Stored ZIP only; compression and recovery next.

### N11-A — bounded native DEFLATE primitive
- [Run 44261123988](https://github.com/poiedk/ps5-custom-payloads/actions/runs/44261123988), commit 015ea11: all three jobs succeeded. Actual host log: `Ran 282 tests in 10.911s` / `OK`.
- zlib 1.4 source hash independently matched in CI: 02dd159783677a749c04adbdd02b55b8a2bcc7e054f51b76b549199a916ad584. Strict output/input length, raw stream termination and expansion bounds; no file writes.
- PR #6 merged into development ONLY at 053fb0d. Read-only ELF artifact 14408445774, SHA-256 3438a449562bbf760016260990281ebb0627dd941767487d2b1db485c958127a.
- ZIP ingestion and actual hardware use remain untested.

### N11-B — native ZIP DEFLATE integration (completed)
- PR #7 merged into development only: `956b185dd757bc3ab1ff8f06ea6fffd1768e8994`.
- Owned decompression buffers for bounded ZIP method 8; legacy stored-only API retained. Manifest verification and managed install/update consume verified entries. CRC, size, traversal, malformed input and cleanup checks retained.
- First CI run 44283890175: 291 tests passed; native job failed before compilation on zlib source checksum/size mismatch. Kept pinned digest unchanged and added bounded fetch retries with identity encoding, no cache, actual hash/size diagnostics and fail-closed behavior.
- Retry CI run 44284150422: all 3 jobs passed; 291 host tests; PS5 SDK cross-build succeeded. Native artifact 14418447322; ELF SHA256 `76a3dd48227e696bef9ebe34dce973c6083e51a130fa8c1ad13aba3d9d7cf2d2`.
- Hardware execution not tested. Artifact remains read-only preflight, not production installer. TAR.GZ native support pending.

### N11-C — native TAR.GZ integration
- [Run 44290886647](https://github.com/poiedk/ps5-custom-payloads/actions/runs/44290886647), commit 114f1b7: all three jobs succeeded. Actual host log: `Ran 303 tests in 11.313s` / `OK`. Native host smoke and SDK cross-build passed.
- Strict single-member gzip expansion validates CRC/ISIZE, full input consumption, bounded expansion. USTAR parser verifies header checksum, ASCII paths, prefix/name fields, size, zero padding and end markers; rejects links, explicit directories, extensions, duplicates and special entries.
- Unified archive-by-content dispatch for manifest verification and native initial install/update; 12 tests exercise malformed archives, memory release, mixed ZIP/TAR update and config preservation.
- PR #8 merged into development ONLY at a75106a. Read-only ELF artifact 14421785930, SHA-256 75de58853a57354ec2aea4e35763e03d6d2a6e821d445e57d8b5fd78de30a75e.
- Strict subset, not general-purpose TAR extraction; no PS5 execution or memory benchmark. Next: recovery inspection and fault-injection gates.

### N12-A — native read-only recovery inspection
- [Run 44291496578](https://github.com/poiedk/ps5-custom-payloads/actions/runs/44291496578), commit c5ba8b6: all three jobs succeeded. Actual host log: `Ran 314 tests in 13.592s` / `OK`. Cross-compilation succeeded.
- 11 new tests cover absent state without writes, active file integrity, mutable configuration changes, damaged/missing data, malformed marker, interrupted staging/pending marker, symlink and lock rejection, and retained snapshot verification.
- PR #9 merged into development ONLY at 2e0eee5. Read-only ELF artifact 14421985940, SHA-256 818ba6cc7101168716ca1fd6bef7b765e1ef98d5a26d317b18f57903da736f6a.
- Reports inactive generations/backups as counts, not authenticated restore candidates. No automatic repair or removal. Next: process-interruption fault tests, then explicit recovery policy. No physical PS5 power-loss test.

### N12-B — isolated process interruption tests
- [Run 44291987774](https://github.com/poiedk/ps5-custom-payloads/actions/runs/44291987774), commit b7874ea: all three jobs succeeded. Actual host log: `Ran 324 tests in 13.227s` / `OK`; native preflight host smoke and SDK cross-build passed.
- Ten Linux-only process-exit tests wrap renameat in the test library, terminate the child process before/after staging publication or active marker rename, and inspect the persisted managed state for installation, update, rollback and uninstall. No fault hooks in the production build.
- PR #10 merged into development ONLY at 340282f. Read-only ELF artifact 14421503531, SHA-256 818ba6cc7101168716ca1fd6bef7b765e1ef98d5a26d317b18f57903da736f6a.
- Process termination is not a simulated storage power loss and does not establish PS5 durability. Inactive/staged generations and pending markers remain retained; explicit recovery/retry policy and native daemon are still pending.

### N12-C — explicit non-destructive recovery retry
- [Run 44365914969](https://github.com/poiedk/ps5-custom-payloads/actions/runs/44365914969), commit 8baee55: all 3 CI jobs succeeded. Actual log: `Ran 334 tests in 15.751s` / `OK`; SDK cross-build succeeded.
- 10 additional tests cover retry after an interrupted initial publication, preserved staged content, active generation protection, stale observations, corrupt active state, symlink refusal, and quarantine collisions.
- PR #11 merged into development ONLY at 4a6eeaf. Read-only ELF artifact 14456915854, SHA-256 a98f2752eabe3b8592e6fe0acf26edfbe7494ed32dc486f299307e436a07fdf8.
- Explicit quarantine of one named remnant only; existing lock, checked CURRENT marker/identity, integrity and private types. Move to separate recovery-quarantine hierarchy without deletion or overwrite; rerun the original verified action after inspection. Invalid CURRENT or corrupt state stays blocked for manual investigation; no automatic reconstruction or promotion. No hardware execution.

### N13-A — authenticated native HTTP protocol and read-only dispatch
- [Run 44366761800](https://github.com/poiedk/ps5-custom-payloads/actions/runs/44366761800), commit 51eab27: all three jobs succeeded. Actual host log: `Ran 344 tests in 12.616s` / `OK`; SDK cross-build succeeded.
- Ten new tests cover authenticated health/status/recovery, exact loopback Host, optional matching Origin, duplicate headers, framing, no bodies or mutations, strict package IDs, bounded replies and no store writes.
- PR #12 merged into development ONLY at 80d2e4b. Read-only ELF artifact 14458050149, SHA-256 fc3345220870804f75fb1fbd994d0837e84d2501e3e2882cefe7f6a54bdc6e88.
- Parser/dispatcher only. No listening socket, token generation or runtime entry point yet. No hardware execution.

### N13-B — actual native loopback TCP transport
- [Run 44368700977](https://github.com/poiedk/ps5-custom-payloads/actions/runs/44368700977), commit 3ec8d0d: all three jobs succeeded. Actual host log: `Ran 352 tests in 16.614s` / `OK`; native preflight cross-build passed.
- Eight Linux socket tests cover loopback-only binding, authenticated fragmented requests, invalid Host, timeout, bounds and sequential reuse. No PS5 runtime test.
- Runs 44367559486 and 44368049604 failed source download integrity (zlib); 44368459801 verified source but failed SDK compilation on INADDR_LOOPBACK. Fixed portable IPv4 loopback constant, retained pinned zlib digest, verified archived source-only fallback in successful run. Fallback artifact is expiring, not a permanent dependency mirror.
- PR #13 merged into development ONLY at 84c3a7a. Preflight artifact 14457962368, ELF SHA256 ec843bfc688e035c4805e4f76b5f77790e824657a6b57b607a6a3f61c41227d9.
- Socket I/O deadline does not bound a store lock wait. No entry point, autostart, LAN binding or mutations yet.

### N13-C — separate explicit read-only runtime
- [Run 44371605704](https://github.com/poiedk/ps5-custom-payloads/actions/runs/44371605704), commit aab519d: all three jobs succeeded. Actual host log: `Ran 358 tests in 19.858s` / `OK`. SDK cross-compiled both distinct ELF targets.
- Six host process tests cover explicit arguments, existing private directory, symlink refusal, fresh entropy token and authenticated socket session with expiry. No default listener or filesystem writes.
- PR #14 merged into development ONLY at 87d1189. Read-only runtime development artifact 14459351447, ELF SHA-256 dbf09ec2183810febaec50c2d8c2dc5b546409155ce9961e528e205d534e70a8. Preflight artifact 14459456295, unchanged ELF SHA-256 ec843bfc688e035c4805e4f76b5f77790e824657a6b57b607a6a3f61c41227d9.
- Loopback only. Requires explicit argv, secure entropy and local launcher output; no PS5 launcher, browser or hardware verification. Store lock wait may delay session exit. Runtime is not an installer or release candidate.

### N13-D — confirmed managed control protocol
- [Run 44372464719](https://github.com/poiedk/ps5-custom-payloads/actions/runs/44372464719), c14ee9a: all three jobs succeeded. Actual host log: `Ran 366 tests in 17.871s` / `OK`. Both ELF builds cross-compiled.
- Eight tests for POST authentication and confirmation, strict arguments, backup/rollback/uninstall/quarantine and isolation from read-only dispatch. PR #15 merged into development only at 9d658c2ca6df8da89a5d9b046f239f0acf9cc3d7.
- Runtime artifact 14460610499, SHA-256 3be8d66743b00d7223ec4eee4799c28060585c7410da4a3456aa79ca9cde8958. Mutation API still not wired to sockets. No hardware test.
