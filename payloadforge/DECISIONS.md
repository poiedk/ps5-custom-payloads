# Decisions

- Keep existing PLDMGR IDs and URL; never publish from a development branch.
- Use opt-in archive policy and explicit exact member selection; do not infer installation paths from ZIP contents.
- SHA-256 verifies integrity, not author identity or binary safety.
- Hold unverified sources and packages with unknown redistribution permissions.
- Keep native build and hardware conclusions separate from host-side Python.
- Stage 2: prefer standard-library TAR.GZ; defer 7Z in v1 to avoid an additional parser/dependency and native-port complexity.

- Stage 4: use immutable managed generations and a single atomic CURRENT pointer, not in-place overwrites. Managed callers resolve the active generation. The root must be private; external application-specific layouts and executable companion files are not approved yet.
- Stage 5: dependency constraints are explicit AND comparisons over numeric semantic versions; no automatic fetching or silent upgrades. Unknown or incompatible constraints block an install.
