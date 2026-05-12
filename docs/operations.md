# Agentic OS Operations

Use this guide for local install, update, verification, and rollback of the global `aos` command. These steps manage only the command symlink. They do not copy private OS home files, memory, secrets, or project data.

## Preconditions

Run from the standalone AOS repository root:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
scripts/readiness_smoke.py --launcher bin/aos --json
scripts/fresh_user_smoke.py --repo-root . --json
```

Both commands must pass before changing a live global command.

## Status

Inspect the current global command target:

```bash
python3 scripts/manage_global_aos.py status --install-dir ~/.local/bin
command -v aos
aos version
aos doctor --summary
```

If `aos doctor --summary` reports sandbox-only permission issues inside a restricted runner, rerun it from a normal local shell before changing the install.

## Install

For normal local usage, run the install wrapper:

```bash
sh scripts/install.sh
```

The wrapper runs the unit suite, runs the repo-contained smoke check, links `bin/aos` into `~/.local/bin`, and verifies the installed command against a temporary OS home. It does not initialize or copy private data into the live `~/.agentic-os` home.

Set `AOS_INSTALL_DIR` to install the command somewhere else:

```bash
AOS_INSTALL_DIR=/tmp/aos-bin sh scripts/install.sh
```

Set `AOS_INSTALL_SKIP_CHECKS=1` only in controlled tests or after a separate release gate has already passed:

```bash
AOS_INSTALL_DIR=/tmp/aos-bin AOS_INSTALL_SKIP_CHECKS=1 sh scripts/install.sh
```

Set `AOS_INSTALL_CHECK_HOME` when you want to inspect the temporary verification OS home yourself:

```bash
AOS_INSTALL_CHECK_HOME=/tmp/aos-install-check sh scripts/install.sh
```

Set `AOS_INSTALL_LAUNCHER` only when validating or installing a non-default launcher path:

```bash
AOS_INSTALL_LAUNCHER=/tmp/agentic-os/bin/aos AOS_INSTALL_DIR=/tmp/aos-bin sh scripts/install.sh
```

For lower-level installs, install the repo-contained launcher as `~/.local/bin/aos`:

```bash
python3 scripts/manage_global_aos.py install --launcher bin/aos --install-dir ~/.local/bin
aos version
aos doctor --summary
```

The installer creates `~/.local/bin` when needed. If an `aos` file already exists, it is moved to a timestamped backup and recorded in `.aos-install-state.json`.

## Update

After pulling or cloning a newer standalone repository, update the global command to point at the checked-out launcher:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
scripts/readiness_smoke.py --launcher bin/aos --json
python3 scripts/manage_global_aos.py update --launcher bin/aos --install-dir ~/.local/bin
aos version
aos doctor --summary
```

`update` is intentionally the same safe activation flow as `install`: it backs up the previous `aos` command before replacing it with a symlink to the selected launcher.

## Rollback

Restore the last command that was replaced by `install` or `update`:

```bash
python3 scripts/manage_global_aos.py rollback --install-dir ~/.local/bin
aos version
aos doctor --summary
```

If there was no previous command, rollback removes the symlink that was created by the last install.

## Release Upgrade Smoke

Before publishing a public alpha after the first release, verify update and rollback across release refs:

```bash
aos release-upgrade-smoke --repo-root . --from-ref v0.1.11-public-alpha --to-ref HEAD --json
```

For a stricter release gate, run the integrated opt-in check:

```bash
aos release-check --repo-root . --upgrade-smoke --from-ref v0.1.11-public-alpha --to-ref HEAD --json
```

The smoke check clones both refs into a temporary workspace, installs the previous launcher into a temporary `aos` command path, updates to the current launcher, rolls back to the previous launcher, and verifies `aos version --json` after each state transition. It does not touch the live global command or live AOS home.

## Public Release Gate

Before publishing a public alpha, run the canonical gate from the public repository:

```bash
aos public-release-gate --repo-root . --json
```

This runs full-history `public-audit` and strict `release-check` with release manifest verification, fresh-user memory smoke, and upgrade smoke enabled. It infers the previous public-alpha tag from git tags when `--from-ref` is omitted. Use `--tree-only` only for development or standalone CI repositories whose git history is not intended for publication.

## Release Install Smoke

After the public tag exists, verify that the published source can be fetched and installed independently:

```bash
aos release-install-smoke --source https://github.com/Dai202703/agentic-os-public-alpha.git --ref v0.1.13-public-alpha --expected-tag v0.1.13-public-alpha --json
```

This smoke fetches the requested tag into a temporary checkout, runs `scripts/install.sh` with temporary install and OS-home paths, verifies the installed `aos` symlink points to the fetched release, and compares `aos version --json` to the release metadata. It does not touch the live global command or live `~/.agentic-os` home.

## Release Manifest

`aos public-export` writes `public-release-manifest.json` with the exported file list and SHA-256 checksum for each file:

```bash
aos public-export --repo-root . --output /tmp/agentic-os-public --json
```

Run `aos release-check --repo-root . --json` from the exported package or public repository to verify the manifest. The `release_manifest` step fails if a release file is missing, unlisted, or has a stale checksum.

## Fresh User Smoke

Before publishing a public alpha or handing AOS to another user, verify the first-use path:

```bash
aos fresh-user-smoke --repo-root . --json
aos release-check --repo-root . --fresh-user-smoke --json
```

The smoke creates a temporary install directory, temporary OS home, and temporary demo project. It runs `scripts/install.sh`, initializes the temporary OS home, links the demo project with Codex, Claude Code, Gemini, and ChatGPT, compiles all provider outputs, runs `aos onboarding-check`, records a session with `memory add session`, verifies it with filtered `memory list`, and recovers it with `memory search`. It does not touch the live global command or live `~/.agentic-os` home.

When the smoke fails, JSON output includes the failed step id, command, path, stdout tail, stderr tail, and `next_action`. Summary output includes the first failed step and the recommended next command to run.

## Project Verification

After install, update, or rollback, verify at least one linked project:

```bash
aos doctor --project-root . --summary
aos version
aos readiness --project-root . --json
aos onboarding-check --project-root . --json
```

`onboarding-check` recompiles provider outputs, verifies the global command, checks strict readiness, and runs the private scan gate.

## Safety Rules

- Do not commit live `~/.agentic-os` contents.
- Do not copy personal memory, identity files, API keys, or machine-specific paths into the standalone repository.
- Do not replace a directory named `aos`; the manager refuses to overwrite directories.
- Keep rollback state in the install directory unless testing with a temporary `--state-file`.
- Run `aos version`, `aos doctor --summary`, and project readiness after every install, update, or rollback.
