# Public Release Policy

This document defines the minimum standard for publishing Agentic OS outside a private repository.

## Release Model

Public releases must be created from a clean export, not by turning a private working repository public.

The public export includes only source code, tests, scripts, provider templates, documentation, CI configuration, and policy files. It must not include generated provider outputs, live OS home files, private memory, client context, local machine paths, or secrets.

## Required Gates

Before a public alpha release:

- `PYTHONPATH=src python3 -m unittest discover -s tests -v` passes.
- `scripts/readiness_smoke.py --launcher bin/aos --json` returns `"ok": true`.
- `aos distribution-check --repo-root . --json` returns `"ok": true`.
- `aos public-audit --repo-root . --json` returns `"ok": true`.
- `aos release-check --repo-root . --json` returns `"ok": true`.
- `aos fresh-user-smoke --repo-root . --json` returns `"ok": true`, including `memory add session`, filtered `memory list`, and `memory search` in the temporary OS home.
- `aos release-check --repo-root . --fresh-user-smoke --json` returns `"ok": true` when validating first-user install behavior.
- `aos release-upgrade-smoke --repo-root . --from-ref v0.1.15-public-alpha --to-ref HEAD --json` returns `"ok": true` for releases after the first public alpha.
- `aos release-check --repo-root . --upgrade-smoke --from-ref v0.1.15-public-alpha --to-ref HEAD --json` returns `"ok": true` when the previous release ref is available.
- `aos public-release-gate --repo-root . --json` returns `"ok": true` as the canonical public release gate.
- After the public tag exists, `aos release-install-smoke --source https://github.com/Dai202703/agentic-os-public-alpha.git --ref v0.1.16-public-alpha --expected-tag v0.1.16-public-alpha --fresh-user-smoke --json` returns `"ok": true`.
- `aos version` reports the expected release tag for the package being published.
- `aos public-export --repo-root . --output /tmp/agentic-os-public --json` creates a clean snapshot.
- `public-release-manifest.json` includes a `sha256` checksum entry for every exported release file.
- The exported snapshot passes `distribution-check`, `public-audit --tree-only`, and `release-check`.
- GitHub Actions passes on the public repository.

## Public Alpha Version

The first public version should be tagged as `v0.1.0-public-alpha`.

The current public alpha line derives release tags from code metadata as `v<version>-public-alpha`; for example, `0.1.16` becomes `v0.1.16-public-alpha`. The `version_consistency` step inside `aos release-check --repo-root . --json` fails when `src/agentic_os/version.py`, `pyproject.toml`, or the top `CHANGELOG.md` heading disagree.

The `release_manifest` step inside `aos release-check --repo-root . --json` fails when `public-release-manifest.json` is missing, lists the wrong files, or has stale SHA-256 checksums.

For `v0.1.16-public-alpha`, the expected direct upgrade smoke source is `v0.1.15-public-alpha`. The canonical `aos public-release-gate --repo-root . --json` infers that previous public-alpha tag automatically from git tags. Use `--from-ref` only when validating an unusual release path.

`aos release-install-smoke` is a post-tag/public-source smoke. It fetches the requested tag from the release source, checks that tag metadata matches `src/agentic_os/version.py`, runs the release installer into a temporary command path, verifies the installed launcher target, and compares `aos version --json` to the release metadata. Use `--fresh-user-smoke` for public handoff validation when the fetched tag should also prove first-user install, provider compile, onboarding, and memory recovery.

The public alpha may change file formats and CLI behavior. Any breaking change should be listed in `CHANGELOG.md`.

## Prohibited Content

Never publish:

- Live `~/.agentic-os` contents
- Generated provider outputs from private projects
- Memory files
- API keys or secret-like strings
- Client-sensitive project context
- Local machine paths
- Private reports or private implementation plans

## Repository Creation

Use a clean export directory as the source of any public repository. Do not expose private git history unless `aos public-audit --repo-root . --json` passes against the full history intended for publication.

`aos public-audit --repo-root . --tree-only --json` is allowed for private development or standalone CI repositories whose history will not be published. It is not sufficient for public release repositories.

`aos release-check --repo-root . --skip-release-manifest --json` is allowed for private development or standalone CI repositories that are not clean public exports and do not contain `public-release-manifest.json`. It is not sufficient for public release repositories.

## Final Public Security Gate

Before tagging, run the strict public gate from the public repository so full git history is scanned:

```bash
aos public-audit --repo-root . --json
aos release-check --repo-root . --fresh-user-smoke --upgrade-smoke --from-ref v0.1.15-public-alpha --to-ref HEAD --json
aos public-release-gate --repo-root . --json
```

After tagging `v0.1.16-public-alpha`, run:

```bash
aos release-install-smoke --source https://github.com/Dai202703/agentic-os-public-alpha.git --ref v0.1.16-public-alpha --expected-tag v0.1.16-public-alpha --fresh-user-smoke --json
```

The final gate must include full-history audit, release manifest verification, fresh-user smoke, upgrade smoke, and generated-output/private-path scanning. `--tree-only` and `--skip-release-manifest` are development shortcuts, not public release gates.

A clean public export does not contain git history. Validate an exported snapshot with `distribution-check`, `public-audit --tree-only`, and strict `release-check`, then sync that export into the public repository before running `public-release-gate`.

## Support Boundaries

Public alpha support is limited to source installs, local file-based workflows, and documented provider outputs. Hosted sync, package-manager distribution, and multi-user administration are future work.
