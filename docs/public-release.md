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
- `aos release-upgrade-smoke --repo-root . --from-ref v0.1.4-public-alpha --to-ref HEAD --json` returns `"ok": true` for releases after the first public alpha.
- `aos release-check --repo-root . --upgrade-smoke --from-ref v0.1.4-public-alpha --to-ref HEAD --json` returns `"ok": true` when the previous release ref is available.
- `aos version` reports the expected release tag for the package being published.
- `aos public-export --repo-root . --output /tmp/agentic-os-public --json` creates a clean snapshot.
- `public-release-manifest.json` includes a `sha256` checksum entry for every exported release file.
- The exported snapshot passes `distribution-check`, `public-audit`, and `release-check`.
- GitHub Actions passes on the public repository.

## Public Alpha Version

The first public version should be tagged as `v0.1.0-public-alpha`.

The current public alpha line derives release tags from code metadata as `v<version>-public-alpha`; for example, `0.1.5` becomes `v0.1.5-public-alpha`. The `version_consistency` step inside `aos release-check --repo-root . --json` fails when `src/agentic_os/version.py`, `pyproject.toml`, or the top `CHANGELOG.md` heading disagree.

The `release_manifest` step inside `aos release-check --repo-root . --json` fails when `public-release-manifest.json` is missing, lists the wrong files, or has stale SHA-256 checksums.

For `v0.1.5-public-alpha`, the expected upgrade smoke source is `v0.1.4-public-alpha`. Future public alpha releases should update the `--from-ref` value to the immediately previous public tag before publishing.

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

## Support Boundaries

Public alpha support is limited to source installs, local file-based workflows, and documented provider outputs. Hosted sync, package-manager distribution, and multi-user administration are future work.
