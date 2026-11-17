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
