# PayloadForge — host development preview

PayloadForge complements PLDMGR by handling reviewed homebrew companion data. Original PayloadForge code: GPL-3.0-or-later (see COPYING). Third-party projects retain their licenses. The production PLDMGR catalog and stable IDs have not been changed by this work.

## Implemented and CI-tested on host
- ZIP/TAR.GZ standalone release extraction for explicitly opted-in, verified archive sources; content-addressed generated ELF and previous-entry fallback. No live archive source enabled. 7Z deferred.
- ZIP companion verification against an external manifest; schemas 1–3 (data-only files, dependencies, declared resource and version conflicts).
- Private managed generation store with atomic CURRENT marker, registry, verified backup, rollback, uninstall and explicit version management. Configuration is preserved as documented.
- Host CLI and authenticated loopback-only web preview. No automatic payload execution or boot-chain changes.
- Candidate provenance and duplicate guard; read-only companion catalog sidecar linked to unchanged explicit PLDMGR IDs. Sidecar intentionally empty pending source approval.

## Native status
SDK v0.42 cross-compiles the **read-only preflight** ELF in CI. It only exercises C validation primitives and prints a smoke-test result. It is NOT a native installer. The full native archive/manifest/hash/transaction engine, PS5 local web daemon, native application layouts and hardware validation remain unimplemented. Do not use the preflight as an installer.

## Host quick start
From repository root (Python 3, POSIX/Linux; no PS5 required):

```sh
python3 -m pip install 'Pillow>=11,<13'
python3 -m unittest discover -s payloadforge -p 'test_*.py' -v
python3 -m payloadforge.demo_fixture --out /tmp/payloadforge-demo-fixtures
python3 -m payloadforge.cli --root /tmp/payloadforge-managed list
python3 -m payloadforge.server --root /tmp/payloadforge-managed --port 8765
```

Open http://127.0.0.1:8765 on the SAME host. Paste the session token printed by the server. Use a demo ZIP, its JSON manifest and matching ZIP hash from SHA256SUMS. Preview first; mutations require explicit confirmation. The server cannot install executables or access arbitrary PS5 paths.

The active generation stores files under managed-root/apps/<id>/generations/<generation>/data. The registry records actual file hashes. Application-specific external paths and unmanaged processes are not handled. The root must be private; hostile concurrent local writes and PS5 power-loss durability are not covered.

## Development records
- PROGRESS.md: actual CI runs and stage boundaries.
- DECISIONS.md: conservative decisions and known scope.
- HUMAN_TODO.md: hardware gate and exact test plan.
- review-candidates.json: catalog review; no unverified promotion.
- RC.md: host preview and native preflight release policy.

No stable release, deployment, force push, branch deletion or automatic execution.
