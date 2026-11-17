# PayloadForge

Development preview. PayloadForge is a proposed PS5 homebrew bundle installer, not yet a runnable PS5 ELF. The existing PLDMGR source URL and production branch remain unchanged.

## Design
1. Keep standalone ELF downloads in PLDMGR, with stable IDs and upstream SHA-256 checks.
2. For an archive containing only a standalone ELF, verify the upstream archive digest, extract the exact member to a staging directory, and publish only the verified ELF (distribution permissions must be checked first).
3. For packages that need accompanying files, build a separate manifest, show a preview and require user confirmation; never treat a companion archive as an automatically executable payload.
4. Native installer: use a supported PS5 homebrew SDK, restrict writes to explicitly approved application-owned directories, protect existing configuration, stage and verify files, and maintain a rollback journal. No boot-chain changes, arbitrary shell commands, or automatic launch.
5. Exclude duplicates already supplied by the official PLDMGR source.

## Milestones
- [x] Development branch and initial archive validator.
- [x] Dry-run companion manifest validator (data-only files, dedicated root, configuration preservation).
- [x] ZIP companion verification: archive SHA-256, exact file list, per-file SHA-256, sizes, and rejection of traversal and special files.
- [x] Stage 0: verified exact baseline source blobs, 21 local tests passed; added 14 ZIP security regression tests, 35 local tests passed. GitHub Actions run 44161036271 confirmed 35/35 tests; real PS5 tests remain unverified.
- [x] OmniPad versioned asset matcher corrected in development.
- [x] Stage 0 gate: CI success (https://github.com/poiedk/ps5-custom-payloads/actions/runs/44161036271).
- [x] Stage 1 implementation: opt-in ZIP release extraction, content-addressed ELF publication and previous catalog fallback.
- [ ] Stage 1 gate: verify CI on the updated branch (10 new synthetic tests). No live archive source activated.
- [ ] Confirm upstream asset SHA-256 before production promotion.
- [ ] Review archive sources and distribution licenses.
- [ ] Integration tests and verified publish workflow.
- [ ] Native installation, backup and rollback implementation.
- [ ] Native build and real-console testing.
- [ ] Stable release after validation.

## ZIP source opt-in (Stage 1)

An archive source must match a reviewed ZIP asset and include an `archive` object with `member` (exact internal ELF path), `standalone: true` and `redistribution` (HTTPS link to documented permission). The updater requires an upstream SHA-256 digest for the ZIP, refuses extra non-documentation files, verifies the extracted ELF and uses its own SHA-256 in the catalog entry. Generated files are content-addressed under `generated/<id>/<sha256>.elf`. The production workflow publishes only from `main`; no live source is activated in this draft. A permission URL is evidence for manual review, not automatic license verification. Bundles with dependencies remain out of scope for Stage 1.

See projects.md for the review queue. No application is installed by this development preview.
