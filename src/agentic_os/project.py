import re
from pathlib import Path

from agentic_os.paths import ensure_project_file, resolve_project_root


LIST_SECTIONS = {"contexts", "skills", "workflows", "providers"}
DICT_SECTIONS = {"memory", "outputs"}
SAFE_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
KNOWN_PROVIDERS = {"codex", "claude", "gemini", "chatgpt"}
RECENT_MEMORY_LIMIT_KEYS = {"include_recent_sessions", "include_recent_decisions"}


def validate_safe_identifier(value: str, label: str) -> str:
    if not SAFE_IDENTIFIER_PATTERN.fullmatch(value):
        raise ValueError(
            f"{label} must be a safe identifier using letters, numbers, underscores, or hyphens"
        )
    return value


def validate_project_id(project_id: str) -> str:
    return validate_safe_identifier(project_id, "project_id")


def validate_project_config(config: dict[str, object]) -> dict[str, object]:
    project_id = str(config.get("id", ""))
    validate_project_id(project_id)

    name = str(config.get("name", "")).strip()
    if not name:
        raise ValueError("Project config must include a non-empty name")

    contexts = config.get("contexts")
    if not isinstance(contexts, list):
        raise ValueError("Project config must declare a contexts list")
    for context in contexts:
        relative = Path(str(context))
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"Project context must stay inside Agentic OS home: {context}")

    providers = config.get("providers")
    if not isinstance(providers, list):
        raise ValueError("Project config must declare a providers list")
    for provider in providers:
        provider_id = validate_safe_identifier(str(provider), "provider")
        if provider_id not in KNOWN_PROVIDERS:
            raise ValueError(f"Unknown provider in project config: {provider_id}")

    outputs = config.get("outputs", {})
    if outputs and not isinstance(outputs, dict):
        raise ValueError("Project config outputs must be a mapping")
    if isinstance(outputs, dict) and "root" in outputs:
        output_root = Path(str(outputs["root"]))
        if output_root.is_absolute() or ".." in output_root.parts:
            raise ValueError(f"Project output root must be relative and safe: {outputs['root']}")

    memory = config.get("memory", {})
    if memory and not isinstance(memory, dict):
        raise ValueError("Project config memory must be a mapping")
    if isinstance(memory, dict):
        for key in RECENT_MEMORY_LIMIT_KEYS:
            if key in memory:
                validate_recent_memory_limit(memory[key], key)

    return config


def validate_recent_memory_limit(value: object, key: str) -> None:
    if type(value) is not int or value < 0:
        raise ValueError(f"memory.{key} must be a non-negative integer")


def quote_scalar(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def parse_scalar(value: str) -> str | int:
    if len(value) >= 2 and value.startswith('"') and value.endswith('"'):
        return unquote_scalar(value)
    if value.isdigit():
        return int(value)
    return value


def unquote_scalar(value: str) -> str:
    if len(value) < 2 or not value.startswith('"') or not value.endswith('"'):
        return value

    result: list[str] = []
    escaped = False
    for character in value[1:-1]:
        if escaped:
            result.append(character)
            escaped = False
        elif character == "\\":
            escaped = True
        else:
            result.append(character)
    if escaped:
        result.append("\\")
    return "".join(result)


def link_project(
    project_root: str | Path,
    project_id: str,
    name: str,
    project_type: str,
    owner: str,
    providers: list[str],
) -> Path:
    validate_project_id(project_id)
    for provider in providers:
        provider_id = validate_safe_identifier(provider, "provider")
        if provider_id not in KNOWN_PROVIDERS:
            raise ValueError(f"Unknown provider in project config: {provider_id}")

    root = resolve_project_root(project_root)
    config_path = ensure_project_file(root, ".agentic-os/project.yaml")
    output_root = f"outputs/{project_id}"
    provider_lines = "\n".join(f"  - {quote_scalar(provider)}" for provider in providers)

    content = f"""id: {quote_scalar(project_id)}
name: {quote_scalar(name)}
type: {quote_scalar(project_type)}
owner: {quote_scalar(owner)}
contexts:
  - core/identity
  - core/workstyle
  - core/business
memory:
  project_state: {quote_scalar(f"memory/project-state/{project_id}.md")}
  include_recent_sessions: 3
  include_recent_decisions: 5
skills:
  - identity-interview
  - memory-capture
  - instruction-compiler
workflows:
  - idea-to-spec
  - session-closeout
outputs:
  root: {quote_scalar(output_root)}
providers:
{provider_lines}
"""
    config_path.write_text(content, encoding="utf-8")
    return config_path


def read_project_config(config_path: str | Path) -> dict[str, object]:
    path = Path(config_path).expanduser().resolve()
    data: dict[str, object] = {}
    current_section: str | None = None

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue

        if not raw_line.startswith(" ") and ":" in raw_line:
            key, value = raw_line.split(":", 1)
            key = key.strip()
            value = value.strip()
            if key in LIST_SECTIONS:
                if value:
                    data[key] = parse_scalar(value)
                    current_section = None
                else:
                    data[key] = []
                    current_section = key
            elif key in DICT_SECTIONS:
                if value:
                    data[key] = parse_scalar(value)
                    current_section = None
                else:
                    data[key] = {}
                    current_section = key
            else:
                data[key] = parse_scalar(value)
                current_section = None
            continue

        if raw_line.startswith("- ") and current_section:
            raise ValueError(f"Project config section {current_section} requires indented '- ' list items")

        if raw_line.startswith("  - ") and current_section:
            section = data[current_section]
            if isinstance(section, list):
                section.append(unquote_scalar(raw_line[4:].strip()))
            else:
                raise ValueError(f"Project config section {current_section} is not a list")
            continue

        if raw_line.startswith("  ") and current_section:
            section = data[current_section]
            if isinstance(section, dict):
                if ":" not in raw_line:
                    raise ValueError(f"Project config section {current_section} requires key/value items")
                key, value = raw_line.strip().split(":", 1)
                section[key.strip()] = parse_scalar(value.strip())
            elif isinstance(section, list):
                raise ValueError(f"Project config section {current_section} requires '- ' list items")
            else:
                raise ValueError(f"Project config section {current_section} has invalid structure")
            continue

        raise ValueError(f"Unsupported project config line: {raw_line.strip()}")

    return data
