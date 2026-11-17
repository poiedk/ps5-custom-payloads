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
