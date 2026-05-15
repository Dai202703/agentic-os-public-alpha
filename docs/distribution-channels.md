# Distribution Channels

The v0.1.17 public alpha still treats GitHub source install as the supported path. Wider package channels should wait until user validation proves that install, PATH, doctor, memory, provider compile, update, and rollback are understandable.

## Current Supported Channel

GitHub source install:

```bash
git clone https://github.com/Dai202703/agentic-os-public-alpha.git
cd agentic-os-public-alpha
sh scripts/install.sh
```

Windows PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install.ps1
```

This channel is preferred for the public alpha because it keeps the full test suite, release gates, docs, and source visible.

## Candidate Channels

### pipx

Best fit for Python CLI users. It can provide isolated installs without requiring users to manage virtual environments directly.

Adopt only after:

- `pyproject.toml` has package metadata ready for public package indexes.
- Release artifacts are built and checked in CI.
- `pipx install agentic-os` can run `aos version` and `aos doctor --summary`.

### PyPI

Best fit for broad Python distribution. It creates a stronger public maintenance obligation than source install.

Adopt only after:

- Version tags, GitHub Releases, and package artifacts are consistent.
- Release signing or checksum guidance is documented.
- The README clearly separates source install from package install.

### Homebrew

Best fit for macOS users who expect `brew install`.

Adopt only after:

- Source install feedback shows macOS PATH confusion is still a major friction point.
- A formula can run a post-install `aos version` smoke.
- Rollback guidance remains clear.

### winget

Best fit for native Windows users.

Adopt only after:

- PowerShell installer validation passes for multiple external Windows machines.
- PATH behavior is understood by non-developer users.
- Signed release artifacts are available or the risk is explicitly documented.

## Decision Rule

Do not add a new channel just to look mature. Add one only when it removes a validated user friction point and can be covered by CI or a repeatable manual release checklist.
