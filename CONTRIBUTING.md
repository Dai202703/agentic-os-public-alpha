# Contributing

Agentic OS is a public alpha. Contributions should keep the project local-first, provider-neutral, and safe for public distribution.

## Development Setup

```bash
git clone https://github.com/Dai202703/agentic-os-public-alpha.git
cd agentic-os-public-alpha
PYTHONPATH=src python3 -m unittest discover -s tests -v
scripts/readiness_smoke.py --launcher bin/aos --json
```

## Pull Request Checklist

- Add or update tests for behavior changes.
- Run the full unittest suite.
- Run `aos distribution-check --repo-root . --json`.
- Run `aos public-audit --repo-root . --json`.
- Run `aos release-check --repo-root . --json`.
- Do not include generated provider outputs, private memory, API keys, client context, or machine-specific local paths.

## Design Principles

- Prefer local files over hosted dependencies.
- Keep provider adapters replaceable.
- Keep private data outside shareable source packages.
- Make failure modes explicit and machine-readable.
- Favor small commands that can be tested with temporary directories.
