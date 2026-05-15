# Changelog

## v0.1.16-public-alpha

- Added Korean and Japanese README guides so non-English users can understand the first-run flow, category freedom, memory workflow, provider outputs, and privacy boundaries before installing.
- Linked multilingual docs from the main README and added artifact coverage to keep the translated onboarding path present in public exports.

## v0.1.15-public-alpha

- Added native Windows install validation, clearer platform-specific install/update/rollback guidance, and public-safe visual onboarding assets for first-run workflows.
- Added memory command templates and workflow guidance so users can capture session and decision memory consistently before recompiling provider instructions.
- Strengthened public release privacy validation with broader secret/path detection, symlink export rejection, and final public security gate documentation.

## v0.1.14-public-alpha

- Added an opt-in fresh-user gate to `aos release-install-smoke` so published public tags can be fetched, installed, version-checked, and then validated through the full first-user install, provider compile, onboarding, and memory workflow.
- Added `--release-install-fresh-user-smoke` to `aos public-release-gate` for post-tag public-source validation with nested fresh-user diagnostics.
- Improved release handoff usability with clearer CLI help text, release-check first-failure summaries, install script step markers, and updated v0.1.14 release documentation.

## v0.1.13-public-alpha

- Added `aos release-install-smoke` to verify a published release ref can be fetched, installed into a temporary command path, and version-checked.
- Added optional `public-release-gate` release install smoke inputs for post-tag public-source validation.
- Updated public-alpha CI and release docs to run the install smoke only for public release tag builds.

## v0.1.12-public-alpha

- Added previous public-alpha tag inference to `aos public-release-gate` when `--from-ref` is omitted.
- Updated public-alpha CI to run the canonical release gate without a hardcoded previous tag.
- Preserved `--from-ref` as an explicit override for unusual release validation cases.

## v0.1.11-public-alpha

- Added `aos public-release-gate` as a canonical public release gate that bundles full public audit, release manifest, fresh-user memory smoke, and upgrade smoke validation.
- Preserved nested release-check and public-audit diagnostics in public release gate JSON output.
- Preserved release-upgrade smoke command and output tails inside `release-check` failure diagnostics.

## v0.1.10-public-alpha

- Extended `aos fresh-user-smoke` to verify first-user memory capture with `memory add session`, filtered `memory list`, and `memory search` against a temporary OS home.
- Added fail-fast memory diagnostics and default live OS-home leakage checks for fresh-user memory smoke output.

## v0.1.9-public-alpha

- Added `aos release-check --skip-release-manifest` for standalone CI repositories that are not clean public exports.
- Updated GitHub Actions to keep full release manifest validation on `Dai202703/agentic-os-public-alpha` while skipping the generated manifest gate in non-public repositories.

## v0.1.8-public-alpha

- Added explicit `aos public-audit --tree-only` mode for current-tree public audit checks in development and standalone CI repositories.
- Updated GitHub Actions to keep full git-history public audit on `Dai202703/agentic-os-public-alpha` while using tree-only audit for non-public repositories.

## v0.1.7-public-alpha

- Added actionable `next_action` diagnostics to `aos fresh-user-smoke` failure reports.
- Preserved fresh-user smoke failure command, path, stdout tail, stderr tail, and next action inside `aos release-check --fresh-user-smoke`.

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
