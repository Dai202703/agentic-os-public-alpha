DIRECTORIES = [
    "core/identity",
    "core/workstyle",
    "core/business",
    "core/team",
    "core/operating-principles",
    "memory/decisions",
    "memory/sessions",
    "memory/learnings",
    "memory/project-state",
    "skills",
    "workflows",
    "providers/codex",
    "providers/claude",
    "providers/gemini",
    "providers/chatgpt",
    "projects",
    "outputs",
    "templates",
    "config",
]

STARTER_FILES = {
    "core/identity/user.md": """# User Identity

## Role
Dai builds AI-assisted business and product systems.

## Long-Term Goals
- Build a personal Agentic OS.
- Improve AI-assisted productivity across projects.
- Prepare a team-distributable operating system.

## Decision Preferences
- Prefer pragmatic, testable steps.
- Keep private data separate from shareable templates.
""",
    "core/identity/assistant-style.md": """# Assistant Style

The assistant should be direct, practical, and implementation-minded. It should preserve context, state assumptions clearly, and keep unrelated work out of scope.
""",
    "core/workstyle/principles.md": """# Workstyle Principles

- Start with context.
- Convert ambiguous ideas into specs.
- Convert approved specs into implementation plans.
- Verify changes before claiming completion.
- Record durable decisions and next actions.
""",
    "core/business/portfolio.md": """# Business Portfolio

This file lists active businesses, experiments, and project families that may need context during AI-assisted work.
""",
    "core/business/brand.md": """# Brand Context

Use this file for shared positioning, voice, and messaging rules.
""",
    "core/business/customer.md": """# Customer Context

Use this file for target users, customer segments, audience constraints, and buying triggers.
""",
    "core/team/collaboration.md": """# Team Collaboration

Team-facing Agentic OS assets should be clear, private-data safe, and easy to install.
""",
    "core/team/distribution-boundaries.md": """# Distribution Boundaries

Private local files stay out of team packages. Share templates, skills, workflows, provider adapters, and docs only after review.
""",
    "config/os.yaml": """version: 1
default_providers:
  - codex
  - claude
""",
    "providers/codex/adapter.yaml": """provider: codex
template: AGENTS.template.md
output: AGENTS.md
""",
    "providers/codex/AGENTS.template.md": """# Agentic OS Context For Codex

Project: {{project_name}} (`{{project_id}}`)
Provider: {{provider}}
Generated: {{generated_at}}

## Loaded Context

{{context_bundle}}
""",
    "providers/claude/adapter.yaml": """provider: claude
template: CLAUDE.template.md
output: CLAUDE.md
""",
    "providers/claude/CLAUDE.template.md": """# Agentic OS Context For Claude Code

Project: {{project_name}} (`{{project_id}}`)
Provider: {{provider}}
Generated: {{generated_at}}

## Loaded Context

{{context_bundle}}
""",
    "providers/gemini/adapter.yaml": """provider: gemini
template: GEMINI.template.md
output: GEMINI.md
""",
    "providers/gemini/GEMINI.template.md": """# Agentic OS Context For Gemini

Project: {{project_name}} (`{{project_id}}`)
Provider: {{provider}}
Generated: {{generated_at}}

## Loaded Context

{{context_bundle}}
""",
    "providers/chatgpt/adapter.yaml": """provider: chatgpt
template: project-instructions.template.md
output: .agentic-os/chatgpt-project-instructions.md
""",
    "providers/chatgpt/project-instructions.template.md": """# Agentic OS Context For ChatGPT

Project: {{project_name}} (`{{project_id}}`)
Provider: {{provider}}
Generated: {{generated_at}}

## Loaded Context

{{context_bundle}}
""",
}
