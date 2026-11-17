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
- [x] Stage 0: verified exact baseline source blobs, 21 local tests passed; added 14 ZIP security regression tests, 35 local tests passed. Remote CI and real PS5 tests remain unverified.
- [x] OmniPad versioned asset matcher corrected in development.
- [ ] Stage 0 gate: confirm GitHub Actions result before Stage 1.
- [ ] Confirm upstream asset SHA-256 before production promotion.
- [ ] Review archive sources and distribution licenses.
- [ ] Integration tests and verified publish workflow.
- [ ] Native installation, backup and rollback implementation.
- [ ] Native build and real-console testing.
- [ ] Stable release after validation.

See projects.md for the review queue. No application is installed by this development preview.
