from datetime import datetime
from pathlib import Path
import re

from .paths import ensure_managed_directory, ensure_managed_file, resolve_os_home

SAFE_PROJECT_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")


def add_session_memory(
    os_home: str | Path | None,
    project_id: str,
    title: str,
    summary: str,
    next_actions: list[str] | None = None,
    timestamp: str | None = None,
    tags: list[str] | None = None,
    decisions: list[str] | None = None,
    artifacts: list[str] | None = None,
) -> Path:
    root = resolve_os_home(os_home)
    validate_project_id(project_id)
    title = normalize_required_single_line(title, "Session title must not be empty")
    summary = normalize_required_single_line(summary, "Session summary must not be empty")
    parsed_time = parse_timestamp(timestamp)
    slug = slugify(title)
    session_dir = ensure_managed_directory(root, "memory/sessions")
    session_path = unique_session_path(
        session_dir,
        f"{parsed_time.strftime('%Y-%m-%d-%H%M')}-{slug}",
    )
    session_path = ensure_managed_file(root, Path("memory/sessions") / session_path.name)

    actions = normalize_optional_list(next_actions)
    tag_items = normalize_optional_list(tags)
    decision_items = normalize_optional_list(decisions)
    artifact_items = normalize_optional_list(artifacts)
    tag_block = render_metadata_tags(tag_items)
    action_block = render_markdown_list(actions, "No next actions recorded")
    decision_block = render_markdown_list(decision_items, "No decisions recorded")
    artifact_block = render_markdown_list(artifact_items, "No artifacts recorded")
    content = f"""---
type: "session"
project_id: {quote_metadata_value(project_id)}
title: {quote_metadata_value(title)}
timestamp: {quote_metadata_value(parsed_time.strftime('%Y-%m-%d %H:%M'))}
{tag_block}
---

# {title}

**Project:** {project_id}
**Timestamp:** {parsed_time.strftime('%Y-%m-%d %H:%M')}

## Summary

{summary}

## Decisions

{decision_block}

## Artifacts

{artifact_block}

## Next Actions

{action_block}
"""
    session_path.write_text(content, encoding="utf-8")
    update_project_state(root, project_id, title, parsed_time)
    return session_path


def add_decision_memory(
    os_home: str | Path | None,
    project_id: str,
    title: str,
    rationale: str,
    timestamp: str | None = None,
) -> Path:
    root = resolve_os_home(os_home)
    validate_project_id(project_id)
    title = normalize_required_single_line(title, "Decision title must not be empty")
    rationale = normalize_required_block(rationale, "Decision rationale must not be empty")
    parsed_time = parse_timestamp(timestamp)
    slug = slugify(title)
    decision_dir = ensure_managed_directory(root, "memory/decisions")
    decision_path = unique_session_path(
        decision_dir,
        f"{parsed_time.strftime('%Y-%m-%d-%H%M')}-{slug}",
    )
    decision_path = ensure_managed_file(root, Path("memory/decisions") / decision_path.name)

    content = f"""---
type: "decision"
project_id: {quote_metadata_value(project_id)}
title: {quote_metadata_value(title)}
timestamp: {quote_metadata_value(parsed_time.strftime('%Y-%m-%d %H:%M'))}
---

# {title}

**Project:** {project_id}
**Timestamp:** {parsed_time.strftime('%Y-%m-%d %H:%M')}

## Rationale

{rationale}
"""
    decision_path.write_text(content, encoding="utf-8")
    update_project_state(root, project_id, title, parsed_time)
    return decision_path


def render_session_memory_template(project_id: str) -> str:
    validate_project_id(project_id)
    return (
        "Session memory template\n\n"
        "Use this after meaningful work, then re-run `aos compile` when you want "
        "new memory reflected in provider instructions.\n\n"
        "```bash\n"
        f"aos memory add session --project-id {project_id} \\\n"
        '  --title "Session title" \\\n'
        '  --summary "What changed, why it matters, and what should persist." \\\n'
        '  --tag "handoff" \\\n'
        '  --decision "Key decision made during the session." \\\n'
        '  --artifact "path/or/link-to-important-output" \\\n'
        '  --next-action "Concrete next step."\n'
        "```\n"
    )


def render_decision_memory_template(project_id: str) -> str:
    validate_project_id(project_id)
    return (
        "Decision memory template\n\n"
        "Use this when a choice should survive across future AI sessions.\n\n"
        "```bash\n"
        f"aos memory add decision --project-id {project_id} \\\n"
        '  --title "Decision title" \\\n'
        '  --rationale "Context, options considered, and why this path was chosen."\n'
        "```\n"
    )


def render_markdown_list(items: list[str], empty_message: str) -> str:
    normalized_items = normalize_optional_list(items)
    return "\n".join(f"- {item}" for item in normalized_items) if normalized_items else f"- {empty_message}"


def render_metadata_tags(tags: list[str]) -> str:
    normalized_tags = normalize_optional_list(tags)
    if not normalized_tags:
        return "tags:"
    quoted_tags = "\n".join(f"  - {quote_metadata_value(tag)}" for tag in normalized_tags)
    return f"tags:\n{quoted_tags}"


def quote_metadata_value(value: str) -> str:
    normalized = normalize_single_line(value)
    escaped = normalized.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def normalize_single_line(value: str) -> str:
    return " ".join(value.split())


def normalize_required_single_line(value: str, error_message: str) -> str:
    normalized = normalize_single_line(value)
    if not normalized:
        raise ValueError(error_message)
    return normalized


def normalize_required_block(value: str, error_message: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(error_message)
    return normalized


def normalize_optional_list(items: list[str] | None) -> list[str]:
    return [normalized for item in items or [] if (normalized := normalize_single_line(item))]


def validate_project_id(project_id: str) -> None:
    if not SAFE_PROJECT_ID_PATTERN.fullmatch(project_id):
        raise ValueError(f"Invalid project id: {project_id}")


def unique_session_path(session_dir: Path, stem: str) -> Path:
    session_path = session_dir / f"{stem}.md"
    suffix = 2
    while session_path.exists():
        session_path = session_dir / f"{stem}-{suffix}.md"
        suffix += 1
    return session_path


def update_project_state(root: Path, project_id: str, title: str, timestamp: datetime) -> Path:
    validate_project_id(project_id)
    title = normalize_required_single_line(title, "Project state title must not be empty")
    ensure_managed_directory(root, "memory/project-state")
    state_path = ensure_managed_file(root, Path("memory/project-state") / f"{project_id}.md")
    entry = f"- {timestamp.strftime('%Y-%m-%d %H:%M')}: {title}\n"
    if state_path.exists():
        existing = state_path.read_text(encoding="utf-8")
        state_path.write_text(existing + entry, encoding="utf-8")
    else:
        state_path.write_text(f"# Project State: {project_id}\n\n{entry}", encoding="utf-8")
    return state_path


def parse_timestamp(value: str | None) -> datetime:
    if value:
        return datetime.strptime(value, "%Y-%m-%d %H:%M")
    return datetime.now()


def slugify(value: str) -> str:
    lowered = value.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    return slug or "session"
