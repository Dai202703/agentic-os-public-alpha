# Security Policy

## Supported Versions

Agentic OS is currently in public alpha. Security fixes target the latest public alpha version.

## Reporting Security Issues

Do not open public issues for vulnerabilities, exposed secrets, or private-data leakage.

Report security issues privately to the repository maintainer through GitHub's private vulnerability reporting feature when available. If private reporting is unavailable, contact the maintainer through the least public channel available on the repository profile.

## Private Data Rules

Agentic OS is local-first. Users are responsible for keeping private context, memory, API keys, client files, and generated provider outputs out of public repositories.

Before publishing or sharing a package, run:

```bash
aos public-audit --repo-root . --json
aos release-check --repo-root . --json
```

## Scope

Security reports should focus on:

- Secret or private-data leakage
- Unsafe file writes outside the requested root
- Symlink or hardlink escape behavior
- Generated provider outputs that include private data unexpectedly
- Install, update, or rollback behavior that can overwrite unrelated files
