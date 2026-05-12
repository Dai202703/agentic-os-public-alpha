# Agentic OS

Agentic OS is a local-first command line toolkit for keeping reusable AI working context, memory, and provider instruction files outside any single AI vendor. It is designed to work with Codex, Claude Code, Gemini, ChatGPT, and future provider adapters through file-based templates.

This repository is prepared as a public alpha. The default design keeps private identity, project memory, client context, API keys, and generated provider outputs outside the shareable source package.

## What It Does

- Initializes a local Agentic OS home, normally `~/.agentic-os`
- Links projects to reusable context files
- Compiles provider instruction files for supported AI tools
- Records session and decision memory in local Markdown files
- Checks project readiness, generated output freshness, and private data risks
- Runs public-release audit, export, and release gates
- Verifies first-user install, onboarding, and memory recovery in isolated temporary folders
- Provides safe install, update, and rollback helpers for the global `aos` command

## Public Alpha Scope

The public alpha is intentionally small and file-based. It does not run a background service, sync private data, or require a hosted account.

Supported provider outputs:

- Codex: `AGENTS.md`
- Claude Code: `CLAUDE.md`
- Gemini: `GEMINI.md`
- ChatGPT: `.agentic-os/chatgpt-project-instructions.md`

## Standalone Install

Clone the public alpha repository and run the verified installer:

```bash
git clone https://github.com/Dai202703/agentic-os-public-alpha.git
cd agentic-os-public-alpha
sh scripts/install.sh
```

`scripts/install.sh` runs the test suite, runs the repo-contained readiness smoke, installs `bin/aos` as a symlink under `~/.local/bin`, prints `aos version`, and verifies the installed command against a temporary OS home. It does not initialize or copy private data into your live `~/.agentic-os` home.

Use `AOS_INSTALL_DIR` when you want to install somewhere else:

```bash
AOS_INSTALL_DIR=/tmp/aos-bin sh scripts/install.sh
```

For lower-level symlink-based installs, updates, and rollbacks:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 scripts/manage_global_aos.py install --launcher bin/aos --install-dir ~/.local/bin
aos version
aos doctor --summary
```

Rollback:

```bash
python3 scripts/manage_global_aos.py rollback --install-dir ~/.local/bin
```

## Quickstart

Create a private OS home:

```bash
aos init
aos version
aos doctor --summary
```

Link a project:

```bash
aos link-project --project-root /tmp/demo-project --id demo --name "Demo Project" --provider codex --provider claude
```

Compile provider instructions:

```bash
aos compile codex --project-root /tmp/demo-project
aos compile claude --project-root /tmp/demo-project
```

Run the linked project gate:

```bash
aos onboarding-check --project-root /tmp/demo-project --json
```

For a linked current working directory:

```bash
aos onboarding-check --project-root . --json
```

## Release And Privacy Gates

Run these from a clean standalone repository before publishing or handing the package to another user:

```bash
aos distribution-check --repo-root . --json
aos public-audit --repo-root . --json
aos release-check --repo-root . --json
aos fresh-user-smoke --repo-root . --json
aos release-check --repo-root . --fresh-user-smoke --json
aos release-upgrade-smoke --repo-root . --from-ref v0.1.9-public-alpha --to-ref HEAD --json
```

Use `aos public-audit --repo-root . --tree-only --json` only for private development or standalone CI repositories whose historical commits are not intended for publication. Public release repositories must run the default full-history audit.
Use `aos release-check --repo-root . --skip-release-manifest --json` only for repositories that are not clean public exports and therefore do not contain `public-release-manifest.json`.

Create a clean public snapshot:

```bash
aos public-export --repo-root . --output /tmp/agentic-os-public --json
```

The gates check for generated provider outputs, live OS home folders, sensitive filenames, API key patterns, private memory references, private local paths, and install rollback failures.
`public-export` writes `public-release-manifest.json` with SHA-256 checksums for exported files.
`release-check` also verifies that code version metadata, `pyproject.toml`, and the top `CHANGELOG.md` release heading agree, and that the release manifest checksum gate passes.
`fresh-user-smoke` verifies an isolated install, temporary OS home, temporary project link, all four provider compiles, onboarding check, `memory add session`, filtered `memory list`, and `memory search` without touching the live OS home or global command. When it fails, JSON and summary output include the failed command, output tails, and a `next_action`.
For release managers, `release-upgrade-smoke` verifies the previous public alpha can be installed, updated to the current ref, and rolled back in an isolated temporary install directory.

## Development

Run from the repository root:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
scripts/readiness_smoke.py --launcher bin/aos --json
```

Run the CLI without installing:

```bash
PYTHONPATH=src python3 -m agentic_os --os-home /tmp/aos-demo init
PYTHONPATH=src python3 -m agentic_os --os-home /tmp/aos-demo doctor
```

## Privacy Model

Shareable source code, provider templates, tests, scripts, and docs belong in this repository.

Private local data belongs in the user's OS home, normally `~/.agentic-os`.

Do not publish:

- Personal identity files from a live OS home
- Private memory
- API keys
- Client-sensitive project state
- Generated provider outputs from private projects
- Machine-specific local paths from a private install

## Documentation

- [Operations](docs/operations.md)
- [Distribution](docs/distribution.md)
- [Public release policy](docs/public-release.md)
- [Security policy](SECURITY.md)
- [Contributing](CONTRIBUTING.md)
