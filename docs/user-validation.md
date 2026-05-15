# Public Alpha User Validation

Use this checklist before calling a public alpha easy to start. The goal is not to prove that AOS works for the maintainer. The goal is to prove that a new user can install it, create a category, save memory, and compile provider outputs without private setup.

## Validation Matrix

Run at least one pass in each environment before a new public alpha handoff:

- macOS with the default `sh scripts/install.sh` flow.
- Windows PowerShell with `powershell -ExecutionPolicy Bypass -File scripts\install.ps1`.
- Linux or WSL with the default shell installer.
- One non-developer user who has not used AOS before.
- One developer user who can inspect failure output and report exact commands.

## Five-Minute Start Pass

A validation pass is successful when a new user can complete this in 5 minutes after cloning the repository:

```bash
sh scripts/install.sh
aos init
aos doctor --summary
mkdir -p /tmp/aos-first-project
aos link-project --project-root /tmp/aos-first-project --id first-project --name "First Project" --provider codex
aos memory add session --project-id first-project --title "First memory" --summary "Use AOS to keep reusable AI context outside one vendor."
aos compile codex --project-root /tmp/aos-first-project
aos onboarding-check --project-root /tmp/aos-first-project --json
```

On Windows PowerShell, replace the install line with:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install.ps1
```

## What To Record

For every test user, record:

- Operating system and shell.
- Install method.
- Whether `aos version` worked immediately after install.
- Whether `aos doctor --summary` returned `0 errors, 0 warnings`.
- Whether provider output was created.
- Time from clone to first provider output.
- First command that failed, if any.
- Confusing README section, if any.
- Whether the user understood that private context stays local.

## Pass Criteria

Treat the public alpha as ready for the next tag only when:

- All required environments complete the five-minute start.
- A non-developer can identify the next command after install.
- A developer can reproduce every release gate from the README.
- No validation note requires a private local path, API key, or live OS home.
- Any failed command has a documented troubleshooting entry.

## Failure Routing

When validation fails:

1. Save the command, terminal output, operating system, and install method.
2. Check [Troubleshooting](troubleshooting.md).
3. Open an issue with the bug report template.
4. Add or update a regression test when the failure is reproducible in the repo.
5. Re-run `aos onboarding-check --project-root . --json` after the fix.
