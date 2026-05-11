from pathlib import Path

from .paths import ensure_managed_directory, ensure_managed_file, resolve_os_home
from .project import quote_scalar, validate_safe_identifier


def create_skill(os_home: str | Path | None, skill_id: str, name: str) -> Path:
    validate_safe_identifier(skill_id, "skill_id")
    root = resolve_os_home(os_home)
    skill_dir = ensure_managed_directory(root, Path("skills") / skill_id)
    ensure_managed_directory(root, Path("skills") / skill_id / "examples")
    ensure_managed_directory(root, Path("skills") / skill_id / "references")

    skill_file = ensure_managed_file(root, Path("skills") / skill_id / "SKILL.md")
    if not skill_file.exists():
        skill_file.write_text(skill_template(skill_id, name), encoding="utf-8")

    learnings_file = ensure_managed_file(root, Path("skills") / skill_id / "learnings.md")
    if not learnings_file.exists():
        learnings_file.write_text(f"# Learnings For {name}\n\n", encoding="utf-8")

    return skill_dir


def create_workflow(os_home: str | Path | None, workflow_id: str, name: str) -> Path:
    validate_safe_identifier(workflow_id, "workflow_id")
    root = resolve_os_home(os_home)
    workflow_dir = ensure_managed_directory(root, Path("workflows") / workflow_id)
    ensure_managed_directory(root, Path("workflows") / workflow_id / "prompts")
    ensure_managed_directory(root, Path("workflows") / workflow_id / "examples")

    workflow_file = ensure_managed_file(root, Path("workflows") / workflow_id / "workflow.yaml")
    if not workflow_file.exists():
        workflow_file.write_text(workflow_yaml(workflow_id, name), encoding="utf-8")

    readme_file = ensure_managed_file(root, Path("workflows") / workflow_id / "README.md")
    if not readme_file.exists():
        readme_file.write_text(f"# {name}\n\nWorkflow ID: `{workflow_id}`\n", encoding="utf-8")

    return workflow_dir


def skill_template(skill_id: str, name: str) -> str:
    return f"""# {name}

**Skill ID:** `{skill_id}`

## Purpose

Describe the repeatable work this skill performs.

## When To Use

- Use this skill when the requested task matches the purpose above.

## Required Inputs

- Task description
- Relevant project context

## Context Files To Load

- core/identity
- core/workstyle

## Process

1. Confirm scope.
2. Load the declared context files.
3. Produce the requested output.
4. Verify the output against the checklist.
5. Record durable learnings in `learnings.md`.

## Output Format

Markdown unless a workflow requires another format.

## Output Location

`outputs/{{project}}/{{workflow}}/{{date}}/`

## Verification Checklist

- The output matches the task.
- Private data is not exposed.
- Next actions are explicit.

## Learning Update Rule

Append reusable improvements to `learnings.md` after the skill is used.
"""


def workflow_yaml(workflow_id: str, name: str) -> str:
    return f"""id: {quote_scalar(workflow_id)}
name: {quote_scalar(name)}
trigger: manual
inputs:
  - task
steps:
  - skill: memory-capture
    review: human
outputs:
  root: outputs/{{project}}/{{workflow}}/{{date}}
  files:
    - final.md
review_points:
  - before_final
stop_conditions:
  - missing_project_link
  - user_rejects_scope
"""
