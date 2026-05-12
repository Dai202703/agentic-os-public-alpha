# Agentic OS Distribution

## Shareable Assets

- CLI source code
- Folder templates
- Provider adapter templates
- Skill templates
- Workflow templates
- Documentation
- Example project configs that do not contain private data

## Private Assets

- Live `~/.agentic-os/core/identity`
- Live `~/.agentic-os/memory`
- API keys and secret-like values
- Private client or project state
- Local machine paths

## Public Alpha Onboarding Flow

1. Clone the Agentic OS repository.
2. Run `sh scripts/install.sh`.
3. Initialize a local OS home with `aos init`.
4. Complete personal identity files.
5. Link one project.
6. Compile one provider instruction file.
7. Record one session memory entry.

## Pre-Distribution AOS Readiness Gate

Before team packaging, the local AOS must pass:

- Full test suite
- Repo-contained global readiness smoke
- OS home doctor
- Project doctor on at least one linked project
- Private data scan warnings reviewed
- Provider compile for all declared providers
- Memory list and search smoke checks

Public package publication requires the additional public release policy in `docs/public-release.md`.

## Release Readiness Check

- The test suite passes.
- `scripts/readiness_smoke.py --launcher bin/aos --json` returns `"ok": true`.
- `aos distribution-check --repo-root . --json` returns `"ok": true`.
- `aos public-audit --repo-root . --json` returns `"ok": true`.
- `aos release-check --repo-root . --json` returns `"ok": true`.
- `aos fresh-user-smoke --repo-root . --json` returns `"ok": true`.
- `aos release-check --repo-root . --fresh-user-smoke --json` returns `"ok": true` when validating first-user install behavior for a public alpha.
- `aos release-check --repo-root . --upgrade-smoke --from-ref v0.1.10-public-alpha --to-ref HEAD --json` returns `"ok": true` when validating a new public alpha against the previous public tag.
- `aos public-release-gate --repo-root . --from-ref v0.1.10-public-alpha --json` returns `"ok": true` as the canonical public release gate.
- `aos public-export --repo-root . --output /tmp/agentic-os-public --json` creates a clean package.
- The clean package includes `public-release-manifest.json` with SHA-256 checksums, and the release manifest checksum gate passes.
- README commands work in a temporary folder.
- `docs/operations.md` covers install, update, rollback, status, and post-change verification.
- No private files are staged or exported.
- Provider templates compile for Codex and Claude.
- A new user can install without any private memory.

## Handoff Verification Gate

This is the minimum gate before handing the standalone repository to another machine or publishing a public alpha:

- Fresh clone test suite passes with `PYTHONPATH=src python3 -m unittest discover -s tests -v`.
- GitHub Actions test workflow passes on the standalone repository.
- Repo-contained smoke passes with `scripts/readiness_smoke.py --launcher bin/aos --json`.
- Install wrapper passes with `sh scripts/install.sh` or with `AOS_INSTALL_DIR` pointed at a temporary bin directory.
- Standalone package privacy gate passes with `aos distribution-check --repo-root . --json`.
- Public release audit passes with `aos public-audit --repo-root . --json`.
- Private development or standalone CI repositories may use `aos public-audit --repo-root . --tree-only --json` only when their git history is not intended for publication.
- Integrated pre-release gate passes with `aos release-check --repo-root . --json`.
- Private development or standalone CI repositories may use `aos release-check --repo-root . --skip-release-manifest --json` only when they are not clean public exports and do not contain `public-release-manifest.json`.
- The integrated pre-release gate includes release manifest checksum verification.
- Fresh user smoke passes with `aos fresh-user-smoke --repo-root . --json`, including `memory add session`, filtered `memory list`, and `memory search` in the temporary OS home.
- The opt-in first-user release gate passes with `aos release-check --repo-root . --fresh-user-smoke --json`.
- The canonical public release gate passes with `aos public-release-gate --repo-root . --from-ref v0.1.10-public-alpha --json`.
- A linked validation project passes `aos onboarding-check --project-root . --json`.
- Generated provider files have no private paths, API keys, private memory references, or client-sensitive details.
- The receiver can reproduce install, doctor, compile, memory, and rollback steps without another user's live `~/.agentic-os` contents.

## Local Global Usage Step

Before modifying a live shell profile or installing into `~/.local/bin`, use the repo-contained launcher:

```bash
bin/aos --os-home /tmp/aos-demo init
scripts/readiness_smoke.py --launcher bin/aos --json
```

The live `~/.agentic-os` home and any global command symlink should be created only after explicit approval for that machine-level installation step.

## Public Snapshot Step

Create public snapshots from a clean export directory:

```bash
aos public-export --repo-root . --output /tmp/agentic-os-public --json
cd /tmp/agentic-os-public
PYTHONPATH=src python3 -m agentic_os public-audit --repo-root . --json
PYTHONPATH=src python3 -m agentic_os release-check --repo-root . --json
PYTHONPATH=src python3 -m agentic_os public-release-gate --repo-root . --from-ref v0.1.10-public-alpha --json
```

Do not make a private working repository public unless the intended published history passes `public-audit`. The `--tree-only` and `--skip-release-manifest` modes are development CI conveniences, not public release gates.
