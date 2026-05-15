# Install AOS For Beginners

This guide is for people who want to use Agentic OS without changing Python code or learning the internals first.

AOS is local-first. No private data is uploaded by the installer or by the `aos` command. Your private OS home is created on your computer, normally at `~/.agentic-os`, and generated provider files are written only into the project folders you link.

## What You Will Install

- A command named `aos`
- A private local AOS home when you run `aos init`
- Project instruction files only when you run `aos compile`
- Markdown memory files only when you run `aos memory add`

The public repository contains source code, tests, scripts, and docs. It does not contain your identity, client context, API keys, or private memory.

## Before You Start

You need:

- A terminal app
- Git
- Python 3
- Internet access for the initial `git clone`

This guide covers macOS, Linux, Windows through WSL, or native Windows PowerShell.

On macOS, open Terminal. If `git --version` opens an Apple developer tools prompt, complete that prompt first. On Linux, install Git and Python 3 with your system package manager if these commands are missing.

Check your tools:

```bash
git --version
python3 --version
```

Native Windows PowerShell users can check Python with either launcher:

```powershell
py -3 --version
python --version
```

If either command is missing, install Git or Python 3 first, then return to this guide.

## Step 1: Download AOS

Choose a folder where you keep tools, then run:

```bash
git clone https://github.com/Dai202703/agentic-os-public-alpha.git
cd agentic-os-public-alpha
```

## Step 2: Run The Installer

macOS, Linux, or Windows through WSL:

```bash
sh scripts/install.sh
```

Native Windows PowerShell. This uses the `scripts/install.ps1` installer file:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install.ps1
```

The native Windows PowerShell installer creates `aos.cmd` and `aos.ps1` launchers. By default it installs under your user app-data folder when available. It prints PATH guidance and only updates your User PATH when you run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install.ps1 -AddToUserPath
```

The installer runs the test suite, runs an isolated readiness check, prints `aos version`, and verifies the installed command with a temporary AOS home. It does not initialize your live private AOS home.

If your terminal says `aos: command not found` after install, close and reopen Terminal. If it still fails, check whether `~/.local/bin` is on your `PATH`.

If native Windows PowerShell says `aos` is not recognized after install, open a new PowerShell window. If you did not use `-AddToUserPath`, either run the generated `aos.cmd` from the install folder shown by the installer or add that install folder to your User PATH.

## Step 3: Create Your Private AOS Home

Run:

```bash
aos init
aos doctor --summary
```

Expected result:

```text
AOS home ok: 0 errors, 0 warnings
```

## Step 4: Link Your First Work Folder

Create a practice folder:

```bash
mkdir -p /tmp/aos-first-project
```

Link it with a category ID you choose:

```bash
aos link-project --project-root /tmp/aos-first-project --id first-project --name "First Project" --provider codex
```

Your category is the `--id` value. You can use your own safe category IDs, such as `book-draft`, `case-research`, `biology-101`, `market-research`, or `product-mvp`.

Use letters, numbers, hyphens, and underscores. Do not use spaces, slashes, private client names, passwords, API keys, or other secrets in category IDs.

## Step 5: Save One Memory

Run:

```bash
aos memory add session --project-id first-project --title "First memory" --summary "Use AOS to keep reusable AI context outside one vendor."
```

Memory should contain durable context: decisions, constraints, next actions, and artifacts you want future AI sessions to remember. Private details stay local in your AOS home. After adding memory, re-run `aos compile` when you want that memory reflected in provider instructions.

List it:

```bash
aos memory list --project-id first-project
```

Search it:

```bash
aos memory search "reusable AI context" --project-id first-project
```

## Step 6: Compile Provider Instructions

Run:

```bash
aos compile codex --project-root /tmp/aos-first-project
```

This writes:

```text
/tmp/aos-first-project/AGENTS.md
```

Open that file if you want to see what AOS generated for Codex.

## How To Know It Worked

Run:

```bash
aos onboarding-check --project-root /tmp/aos-first-project --json
```

The command should return JSON with `"ok": true`.

You can also run:

```bash
aos doctor --project-root /tmp/aos-first-project --summary
```

Expected result:

```text
AOS project ok: 0 errors, 0 warnings
```

## Common Problems

### `git: command not found`

Install Git, then run `git --version` again.

### `python3: command not found`

Install Python 3, then run `python3 --version` again.

### `aos: command not found`

Close and reopen Terminal. If it still fails, make sure `~/.local/bin` is on your `PATH`.

### `AOS home issues`

Run:

```bash
aos doctor
```

Read the action line in the output. It explains what to fix.

### Generated files look stale

Run compile again for the provider you use:

```bash
aos compile codex --project-root /tmp/aos-first-project
```

## Update, Roll Back, Or Uninstall

From the cloned `agentic-os-public-alpha` folder, update the installed command with:

```bash
python3 scripts/manage_global_aos.py update --launcher bin/aos --install-dir ~/.local/bin
```

Windows update from the cloned folder reruns the PowerShell installer:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install.ps1
```

If you installed to a custom Windows folder, pass the same `-InstallDir` value during update and rollback.

Rollback:

```bash
python3 scripts/manage_global_aos.py rollback --install-dir ~/.local/bin
```

Native Windows PowerShell rollback:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install.ps1 -Rollback
```

Uninstall the command:

```bash
rm ~/.local/bin/aos
```

Uninstalling the command does not delete your private `~/.agentic-os` home.

## Next Step

Use AOS on a real folder only after the practice flow passes. Start with one category, one memory, and one provider compile. Add more categories after the first workflow feels predictable.
