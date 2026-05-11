# Agentic OS Operations

Use this guide for local install, update, verification, and rollback of the global `aos` command. These steps manage only the command symlink. They do not copy private OS home files, memory, secrets, or project data.

## Preconditions

Run from the standalone AOS repository root:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
scripts/readiness_smoke.py --launcher bin/aos --json
```

Both commands must pass before changing a live global command.

## Status

Inspect the current global command target:

```bash
python3 scripts/manage_global_aos.py status --install-dir ~/.local/bin
command -v aos
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

For lower-level installs, install the repo-contained launcher as `~/.local/bin/aos`:

```bash
python3 scripts/manage_global_aos.py install --launcher bin/aos --install-dir ~/.local/bin
aos doctor --summary
```

The installer creates `~/.local/bin` when needed. If an `aos` file already exists, it is moved to a timestamped backup and recorded in `.aos-install-state.json`.

## Update

After pulling or cloning a newer standalone repository, update the global command to point at the checked-out launcher:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
scripts/readiness_smoke.py --launcher bin/aos --json
python3 scripts/manage_global_aos.py update --launcher bin/aos --install-dir ~/.local/bin
aos doctor --summary
```

`update` is intentionally the same safe activation flow as `install`: it backs up the previous `aos` command before replacing it with a symlink to the selected launcher.

## Rollback

Restore the last command that was replaced by `install` or `update`:

```bash
python3 scripts/manage_global_aos.py rollback --install-dir ~/.local/bin
aos doctor --summary
```

If there was no previous command, rollback removes the symlink that was created by the last install.

## Project Verification

After install, update, or rollback, verify at least one linked project:

```bash
aos doctor --project-root . --summary
aos readiness --project-root . --json
aos onboarding-check --project-root . --json
```

`onboarding-check` recompiles provider outputs, verifies the global command, checks strict readiness, and runs the private scan gate.

## Safety Rules

- Do not commit live `~/.agentic-os` contents.
- Do not copy personal memory, identity files, API keys, or machine-specific paths into the standalone repository.
- Do not replace a directory named `aos`; the manager refuses to overwrite directories.
- Keep rollback state in the install directory unless testing with a temporary `--state-file`.
- Run `aos doctor --summary` and project readiness after every install, update, or rollback.
