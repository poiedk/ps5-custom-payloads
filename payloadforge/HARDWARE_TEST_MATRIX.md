# Hardware test matrix — isolated demo candidate

All entries begin as NOT_RUN. Use only a CI-verified candidate and the bundled harmless synthetic fixtures. Stop at the first unmet prerequisite. Do not test with real payloads, game files, boot configuration or production PLDMGR paths.

| ID | Prerequisite / action | Expected evidence |
|---|---|---|
| H01 | Record PS5 model, actual firmware and PLDMGR version. Confirm firmware 13.60 without updating it. Verify kit SHA-256 using SHA256SUMS. | Model/version and matching runtime and fixture digests. |
| H02 | Confirm that the already-authorized local launcher can pass the documented runtime arguments and expose local output securely. Confirm private existing demo root and free storage. | Explicit arguments supported, output available, no change to other paths. Otherwise BLOCKED. |
| H03 | Explicit read-only or isolated demo session according to documented invocation. Confirm loopback endpoint, local browser and temporary token; do not expose it outside the console. | Unauthorized API denied, working local UI; no background autoload. |
| H04 | Verify bundled v1 manifest and ZIP; alter a copied expected hash and verify rejection. | Correct identity and digest accepted, bad hash rejected without mutation. |
| H05 | Install synthetic v1 after explicit review and confirmation. | Active demo registry, file hashes, expected v1 asset. |
| H06 | Using an already-authorized local test tool, change ONLY demo settings.json. Verify/install upgrade v2. | User setting preserved, asset v2, verified backup. If no safe local editing mechanism, BLOCKED. |
| H07 | Perform backup and rollback to v1. | Verified snapshot, asset v1, latest config preserved. |
| H08 | Inspect recovery before and after actions; optionally inspect a known synthetic interrupted remnant created by an approved test harness. | No unexpected entries and no automatic cleanup. No physical power interruption; if no harness, interruption test BLOCKED. |
| H09 | Uninstall keep, inspect snapshot and reinstall. Test drop only in fresh synthetic store with verified backup. | Retained settings for keep, registered files only, backup retained. |
| H10 | With demo v1 active after reinstall, pair demo-v1.0.0.zip first with negative-dependencies.json and then with negative-conflicts.json. Use each file’s digest from fixtures/SHA256SUMS and try Install for demo-negative. | Current generation unchanged, explicit refusal. |
| H11 | Use the optional local version check, then confirm existing PLDMGR repository URL, IDs, favorites and settings unaffected. | Before/after comparison; no autoload change. |
| H12 | Record runtime memory/latency, file picker usability, normal shutdown and any errors. | Actual hardware observations; no extrapolation from Linux. |
| H13 | Stop runtime and preserve test evidence. | No continuing listener or unexpected state. |

Report PASS/FAIL/BLOCKED per item using HARDWARE_RESULT_TEMPLATE.json. Never share session tokens, credentials or unrelated personal files. No stable release approval from a partial matrix.
