# Onboarding Package

This package is for team members and public users who need a short path from zero to useful AOS output.

## 10-Minute Flow

This 10-minute flow is the default onboarding path for a first public or team user.

1. Clone the public alpha repository.
2. Run the platform install command.
3. Run `aos version`.
4. Run `aos init`.
5. Run `aos doctor --summary`.
6. Create a disposable first project.
7. Link it with one provider.
8. Add one memory entry.
9. Compile provider outputs.
10. Run `aos onboarding-check --project-root`.

## Team Setup

Teams should keep shared templates and private context separate:

- Shared: public docs, workflow examples, safe category naming, release gates.
- Private context: identity, client names, active project facts, API keys, memory, generated provider outputs.
- Team conventions: safe project IDs, provider list, test commands, memory review cadence.

## Public Users

Public users should start with:

- [Install AOS For Beginners](install-for-beginners.md)
- [Troubleshooting](troubleshooting.md)
- [Role Tutorials](role-tutorials.md)
- [Memory Workflows](memory-workflows.md)

## Private Context Rule

Private context belongs in the local OS home and project workspace. Do not paste private memory, generated provider outputs, private project paths, or secrets into public issues.

## First Useful Memory

Use memory for information that should survive the current AI chat:

```bash
aos memory add session --project-id first-project --title "First setup" --summary "Installed AOS, linked first project, and compiled provider outputs."
```

Then recompile:

```bash
aos compile codex --project-root /tmp/aos-first-project
```

## Provider Outputs

AOS creates provider instruction files that existing AI tools can read:

- Codex: `AGENTS.md`
- Claude Code: `CLAUDE.md`
- Gemini: `GEMINI.md`
- ChatGPT: `.agentic-os/chatgpt-project-instructions.md`

These files are generated. Update context and memory, then compile again.
