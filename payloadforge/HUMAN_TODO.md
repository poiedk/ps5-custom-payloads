# Human tasks (pre-release gate)

No console changes requested yet.

1. Once a native candidate exists, verify its CI artifact and SHA-256, then manually test on an owned PS5 running firmware 13.60; do not enable autoload.
2. Use a disposable test package and back up relevant app-owned data before testing.
3. Verify install, update, preservation of settings, conflict rejection, rollback and uninstall. Record logs and observed file hashes. Test interruption recovery first on a host/sandbox; do not deliberately cut power to a live console.
4. Verify PLDMGR still lists and launches the same existing slots, with unchanged IDs and source URL.
5. Stable release is blocked until all hardware results, compatibility and source/redistribution checks are reviewed.
