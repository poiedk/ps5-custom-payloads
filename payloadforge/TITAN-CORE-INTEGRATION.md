# TITAN CORE v1.0.0 — staged integration checklist

Status: **NOT ENABLED / NO-GO**. Do not merge this draft review PR or add TITAN CORE to active `sources.json` until all gates pass.

## Verified
- Official repository: https://github.com/devchmod/TITAN-CORE
- Release: https://github.com/devchmod/TITAN-CORE/releases/tag/v1.0.0
- Pinned commit: `2e1f186a9778eae0976af2cf24d07bfb435d1b7c`
- ELF asset: `TITAN-CORE-v1.0.elf` (17,391,872 bytes)
- Independent SHA-256 of user-supplied ELF: `50f074700fc4f427ae87fb2cb986ad07d633ef01799077953817a6ffded7f91d` — matches release digest.
- Upstream CI success for pinned commit; does not establish release reproducibility or hardware safety.

## Blocking checks
- [ ] Complete source and dependency security/provenance review.
- [ ] Confirm firmware 13.60 behavior on hardware, using a controlled test.
- [ ] Verify coexistence with the current jailbreak chain; prevent duplicate kstuff/ShadowMountPlus dispatch.
- [ ] Decide whether manual-only, explicit user-triggered launch is acceptable. **No autoload**.
- [ ] Confirm any active catalog entry is checksum-pinned and points only to the official release.
- [ ] Pass repository PR CI and human review before merge.

## Safe integration proposal (NOT applied)
If gates pass, add a source entry with id `titan-core`, repository `devchmod/TITAN-CORE`, and release asset regex `^TITAN-CORE-v[0-9]+\\.[0-9]+\\.elf$`. Keep firmware and boot-chain warning visible in the catalog. Avoid any automatic payload execution.

This file is documentation only and does not change active catalog feeds or PS5 behavior.
