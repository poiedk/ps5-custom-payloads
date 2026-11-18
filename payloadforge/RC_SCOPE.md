# PayloadForge 0.2.0-rc0-demo — scope and gates

This is a CI-built hardware **test candidate**, not a stable release and not a general PS5 payload installer.

- Contents: isolated demo-managed runtime, checksum manifest, synthetic data-only fixtures, corresponding project source, pinned zlib source, hardware matrix and result template. The runtime uses SDK v0.42, pinned in the workflow. The ELF is built for PS5; the complete session and filesystem behavior have not been demonstrated on a PS5.
- Allowed scope: existing private /data/payloadforge-demo only; explicit managed-mode invocation, IPv4 loopback, short-lived session token, no auto-start and no shell or payload execution.
- The embedded PLDMGR reference is a dated immutable snapshot of nine production IDs, not a live source or an import operation. Zero approved companion packages. No source URL, favorites, autoload or PLDMGR files changed.
- Manual upload requires caller-supplied reference digests. Byte integrity is not provenance verification; the UI must not say otherwise. Unknown bundles, binaries and executable package integration are outside this demo.
- The archive limits bound parser input and decompression but are not a measured memory budget for PS5. Only tiny synthetic fixtures should be used during physical testing.
- CLI arguments, local output/session token access, loopback browser, file picker, filesystem permissions and durability are physical gates. A lost response after commit requires read-only inspection, not automatic retry. Do not deliberately interrupt console power.
- Existing staged/quarantined objects are preserved; no automatic reconstruction of corrupt CURRENT. A damaged active installation remains blocked for explicit investigation.

## Upstream compatibility references

- PLDMGR documentation: https://github.com/itsPLK/ps5-payload-manager
- Its v0.6.3 header reviewed on 2026-11-18: https://github.com/itsPLK/ps5-payload-manager/blob/main/include/pldmgr.h
- Custom repositories: https://github.com/itsPLK/ps5-payload-manager/blob/main/CUSTOM_REPOSITORIES.md
- SDK: https://github.com/ps5-payload-dev/sdk/releases/tag/v0.42

The PLDMGR source documents its own port and separate storage/configuration paths. PayloadForge neither invokes its mutation endpoints nor accesses its data directories. Actual interoperability on the console is a distinct hardware gate. No modification of the loader, boot chain or autoload is requested.

## Release policy

The CI candidate artifact appears only if host regressions, real Chromium browser E2E, SDK cross-build and candidate packaging succeed. This establishes a candidate for an isolated demo test, not functional compatibility with console firmware 13.60. Keep production main and the existing PLDMGR source unchanged. Do not publish a stable or full installer release until explicit hardware evidence and source/asset provenance gates are satisfied.
