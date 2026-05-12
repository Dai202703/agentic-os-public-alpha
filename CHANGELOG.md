# Changelog

## v0.1.6-public-alpha

- Added `aos fresh-user-smoke` to verify isolated install, OS home initialization, project link, provider compilation, and onboarding.
- Added optional `aos release-check --fresh-user-smoke` gating for first-user public release validation.

## v0.1.5-public-alpha

- Added SHA-256 checksums to `public-release-manifest.json`.
- Added a release manifest checksum gate to `aos release-check`.

## v0.1.4-public-alpha

- Added `aos release-upgrade-smoke` to verify install, update, rollback, and version traceability across release refs.
- Added optional `aos release-check --upgrade-smoke` gating for release managers.

## v0.1.3-public-alpha

- Added `aos version` and install-time version traceability output.
- Added release metadata consistency checks to `aos release-check`.

## v0.1.2-public-alpha

- Updated GitHub Actions to Node 24 compatible `actions/checkout@v6` and `actions/setup-python@v6`.

## v0.1.1-public-alpha

- Added `scripts/install.sh` for one-command verified local install with `AOS_INSTALL_DIR` support.

## v0.1.0-public-alpha

- Added public release policy, security policy, contribution guide, and license.
- Added `aos public-audit` for current-tree and git-history public-release checks.
- Added `aos public-export` for clean public snapshot creation.
- Added `aos release-check` as an integrated pre-release gate.
- Added `aos distribution-check` for shareable package privacy validation.
- Added tested symlink install, update, status, and rollback operations.
- Added provider output freshness and context coverage checks.
- Added provider compilation for Codex, Claude Code, Gemini, and ChatGPT.
