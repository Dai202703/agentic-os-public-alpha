from datetime import datetime
import hashlib
import json
from pathlib import Path

from .memory_index import list_memory
from .paths import (
    ensure_project_file,
    ensure_readable_file,
    reject_symlink_components,
    resolve_os_home,
    resolve_project_root,
    validate_relative_path,
)
from .project import read_project_config, validate_project_config


RECENT_MEMORY_EXCERPT_LIMIT = 500
FINGERPRINT_LABEL = "Context-Fingerprint"
FINGERPRINT_VERSION = 1
PROVIDER_FILES = {
    "codex": ("providers/codex/AGENTS.template.md", "AGENTS.md"),
    "claude": ("providers/claude/CLAUDE.template.md", "CLAUDE.md"),
    "gemini": ("providers/gemini/GEMINI.template.md", "GEMINI.md"),
    "chatgpt": ("providers/chatgpt/project-instructions.template.md", ".agentic-os/chatgpt-project-instructions.md"),
}


def compile_provider(
    os_home: str | Path | None,
    project_root: str | Path,
    provider: str,
) -> Path:
    if provider not in PROVIDER_FILES:
        known = ", ".join(sorted(PROVIDER_FILES))
        raise ValueError(f"Unknown provider '{provider}'. Known providers: {known}")

    root = resolve_os_home(os_home)
    project_path = resolve_project_root(project_root)
    project_output_root = Path(project_root).expanduser()
    config_path = ensure_readable_file(project_path, ".agentic-os/project.yaml", "Project config")
    config = validate_project_config(read_project_config(config_path))
    declared_providers = config.get("providers")
    if not isinstance(declared_providers, list):
        raise ValueError("Project config must declare a providers list")
    declared_provider_ids = [str(declared_provider) for declared_provider in declared_providers]
    if provider not in declared_provider_ids:
        enabled = ", ".join(declared_provider_ids) or "none"
        raise ValueError(
            f"Provider '{provider}' is not enabled for this project. Enabled providers: {enabled}"
        )

    template_relative, output_relative = PROVIDER_FILES[provider]
    template_path = ensure_readable_file(root, template_relative, "Provider template")
    template = template_path.read_text(encoding="utf-8")
    context_bundle = build_context_bundle(root, config)
    fingerprint = compute_context_fingerprint(provider, config, template, context_bundle)

    rendered = render_template(
        template,
        {
            "project_name": str(config.get("name", "")),
            "project_id": str(config.get("id", "")),
            "provider": provider,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "context_bundle": context_bundle,
        },
    )
    rendered = inject_context_fingerprint(rendered, fingerprint)

    output_path = ensure_project_file(project_output_root, output_relative)
    output_path.write_text(rendered, encoding="utf-8")
    return output_path


def provider_context_fingerprint(os_home: Path, provider: str, config: dict[str, object]) -> str:
    template_relative, _ = PROVIDER_FILES[provider]
    template_path = ensure_readable_file(os_home, template_relative, "Provider template")
    template = template_path.read_text(encoding="utf-8")
    context_bundle = build_context_bundle(os_home, config)
    return compute_context_fingerprint(provider, config, template, context_bundle)


def build_context_bundle(os_home: Path, config: dict[str, object]) -> str:
    context_bundle = collect_context_bundle(os_home, config.get("contexts", []))
    recent_memory = collect_recent_memory(os_home, str(config.get("id", "")), config.get("memory"))
    if recent_memory:
        context_bundle = "\n\n".join(section for section in [context_bundle, recent_memory] if section)
    return context_bundle


def compute_context_fingerprint(
    provider: str,
    config: dict[str, object],
    template: str,
    context_bundle: str,
) -> str:
    payload = {
        "version": FINGERPRINT_VERSION,
        "provider": provider,
        "project_config": config,
        "template": template,
        "context_bundle": context_bundle,
    }
    serialized = json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def inject_context_fingerprint(rendered: str, fingerprint: str) -> str:
    metadata_line = f"{FINGERPRINT_LABEL}: {fingerprint}"
    lines = rendered.splitlines()
    for index, line in enumerate(lines):
        if line.startswith("Generated: "):
            lines.insert(index + 1, metadata_line)
            return "\n".join(lines) + ("\n" if rendered.endswith("\n") else "")
    return f"{metadata_line}\n\n{rendered}"


def extract_context_fingerprint(content: str) -> str | None:
    prefix = f"{FINGERPRINT_LABEL}:"
    for line in content.splitlines():
        if line.startswith(prefix):
            return line[len(prefix):].strip()
    return None


def collect_context_bundle(os_home: Path, contexts: object) -> str:
    if not isinstance(contexts, list):
        return ""

    root = os_home.resolve()
    sections: list[str] = []
    for relative in contexts:
        context_path = resolve_context_path(root, str(relative))
        if not context_path.exists():
            raise FileNotFoundError(context_path)
        if context_path.is_file():
            safe_context_file = ensure_readable_file(
                root,
                context_path.relative_to(root),
                "Context file",
            )
            sections.append(format_context_file(safe_context_file, root))
        elif context_path.is_dir():
            for markdown_file in sorted(context_path.glob("*.md")):
                safe_markdown_file = ensure_readable_file(
                    root,
                    markdown_file.relative_to(root),
                    "Context file",
                )
                sections.append(format_context_file(safe_markdown_file, root))
        else:
            raise ValueError(f"Context path is not a file or directory: {relative}")

    return "\n\n".join(sections)


def collect_recent_memory(os_home: Path, project_id: str, memory_config: object) -> str:
    if not isinstance(memory_config, dict):
        return ""

    session_limit = positive_int_limit(memory_config.get("include_recent_sessions"))
    decision_limit = positive_int_limit(memory_config.get("include_recent_decisions"))
    recent_sessions = (
        list_memory(os_home, project_id=project_id, memory_type="session", limit=session_limit)
        if session_limit is not None
        else []
    )
    recent_decisions = (
        list_memory(os_home, project_id=project_id, memory_type="decision", limit=decision_limit)
        if decision_limit is not None
        else []
    )
    if not recent_sessions and not recent_decisions:
        return ""

    sections = ["## Recent Memory"]
    if recent_sessions:
        sections.append(render_memory_section("## Recent Sessions", recent_sessions, "Summary"))
    if recent_decisions:
        sections.append(render_memory_section("## Recent Decisions", recent_decisions, "Rationale"))
    return "\n\n".join(sections)


def positive_int_limit(value: object) -> int | None:
    if value is None:
        return None
    if type(value) is not int or value < 0:
        raise ValueError("Recent memory include values must be non-negative integers")
    return value if value > 0 else None


def render_memory_section(heading: str, entries: object, excerpt_heading: str) -> str:
    lines = [heading]
    for entry in entries:
        title = normalize_recent_memory_text(entry.title)
        excerpt = extract_memory_heading_text(entry.path, excerpt_heading)
        line = f"- {normalize_recent_memory_text(entry.timestamp)}: {title}"
        if excerpt:
            line = f"{line} - {excerpt}"
        lines.append(line)
    return "\n\n".join([lines[0], "\n".join(lines[1:])])


def extract_memory_heading_text(path: Path, heading: str) -> str:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return ""

    target = f"## {heading}"
    collecting = False
    body_lines: list[str] = []
    for line in lines:
        if collecting:
            if line.startswith("## "):
                break
            body_lines.append(line)
        elif line.strip() == target:
            collecting = True

    return normalize_recent_memory_text("\n".join(body_lines), RECENT_MEMORY_EXCERPT_LIMIT)


def normalize_recent_memory_text(value: object, limit: int | None = None) -> str:
    normalized = " ".join(str(value).split())
    if limit is not None and len(normalized) > limit:
        return normalized[: limit - 1].rstrip() + "..."
    return normalized


def resolve_context_path(os_home: Path, relative: str) -> Path:
    root = os_home.resolve()
    relative_path = validate_relative_path(relative)
    reject_symlink_components(root, relative_path)
    context_path = (root / relative_path).resolve()
    if not context_path.is_relative_to(root):
        raise ValueError(f"Context path escapes Agentic OS home: {relative}")
    return context_path


def format_context_file(path: Path, os_home: Path) -> str:
    relative = path.relative_to(os_home)
    content = path.read_text(encoding="utf-8").strip()
    return f"### {relative}\n\n{content}\n"


def render_template(template: str, values: dict[str, str]) -> str:
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace("{{" + key + "}}", value)
    return rendered
