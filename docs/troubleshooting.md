# Troubleshooting

This guide covers the public alpha problems a first user is most likely to hit. Keep issue reports free of private project names, API keys, client facts, and local home paths.

## `aos` Is Not Found

Check the installed command:

```bash
command -v aos
aos version
```

If `command -v aos` prints nothing, add the install directory to PATH or run the command through the generated launcher path printed by the installer.

macOS, Linux, or WSL default:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Windows PowerShell default:

```powershell
$env:Path
```

Rerun the installer with `-AddToUserPath` only when you want it to edit the User PATH:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install.ps1 -AddToUserPath
```

## Python Is Missing Or Too Old

Check Python before installing:

```bash
python3 --version
python --version
```

Windows PowerShell:

```powershell
py -3 --version
python --version
```

AOS requires Python 3.10 or newer. Install Python from the operating system package manager or from python.org, then rerun the installer.

## PowerShell ExecutionPolicy Blocks Install

Use the documented one-command bypass for the installer process:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install.ps1
```

This does not require changing the machine-wide policy. If a company policy still blocks it, ask the administrator to allow local script execution for this checkout.

## Permission Denied

If install fails with `Permission denied`, install into a user-writable directory:

```bash
AOS_INSTALL_DIR=/tmp/aos-bin sh scripts/install.sh
```

PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install.ps1 -InstallDir "$env:TEMP\aos-bin"
```

Do not use `sudo` unless you intentionally want a system-wide install. Public alpha support assumes user-level installs.

## Doctor Fails

Run:

```bash
aos version
aos doctor --summary
```

For a linked project:

```bash
aos doctor --project-root . --summary
aos onboarding-check --project-root . --json
```

If the project doctor fails, check that `.agentic-os/project.yaml` exists and that generated provider outputs are current. Re-run compile for the provider you use:

```bash
aos compile codex --project-root .
```

## Memory Is Not Appearing In Provider Output

Memory is local. After saving a memory entry, re-run compile:

```bash
aos memory list --project-id demo
aos memory search "important phrase" --project-id demo
aos compile codex --project-root .
```

## Public Issue Reports

When opening an issue, include:

- Operating system.
- Install method.
- Output of `aos version`.
- Output of `aos doctor --summary`.
- The first failed command.

Remove private paths, names, and secrets before posting.
