import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .paths import resolve_os_home


@dataclass(frozen=True)
class MemoryEntry:
    memory_type: str
    project_id: str
    title: str
    timestamp: str
    path: Path


@dataclass(frozen=True)
class MemorySearchResult:
    memory_type: str
    project_id: str
    title: str
    timestamp: str
    path: Path
    snippet: str


def parse_front_matter(path: Path) -> dict[str, object]:
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return {}

    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}

    closing_index = None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            closing_index = index
            break
    if closing_index is None:
        return {}

    metadata: dict[str, object] = {}
    current_list_key: str | None = None
    for line in lines[1:closing_index]:
        if line.startswith("  - ") and current_list_key:
            current_value = metadata.setdefault(current_list_key, [])
            if isinstance(current_value, list):
                current_value.append(_parse_scalar(line[4:].strip()))
            continue

        current_list_key = None
        if ":" not in line or line.startswith(" "):
            continue

        key, raw_value = line.split(":", 1)
        key = key.strip()
        if not key:
            continue

        raw_value = raw_value.strip()
        if raw_value:
            metadata[key] = _parse_scalar(raw_value)
        else:
            metadata[key] = []
            current_list_key = key

    return metadata


def list_memory(
    os_home: str | Path | None,
    project_id: str | None = None,
    memory_type: str | None = None,
    limit: int | None = None,
) -> list[MemoryEntry]:
    if limit is not None and limit < 0:
        raise ValueError("limit must be non-negative")

    entries = [
        entry
        for entry in _iter_memory_entries(resolve_os_home(os_home))
        if _matches_filters(entry, project_id, memory_type)
    ]
    entries.sort(key=lambda entry: entry.timestamp, reverse=True)
    if limit is not None:
        return entries[:limit]
    return entries


def search_memory(
    os_home: str | Path | None,
    query: str,
    project_id: str | None = None,
) -> list[MemorySearchResult]:
    normalized_query = query.casefold()
    if not normalized_query:
        return []

    results: list[MemorySearchResult] = []
    for entry in _iter_memory_entries(resolve_os_home(os_home)):
        if project_id is not None and entry.project_id != project_id:
            continue
        try:
            lines = entry.path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue

        for line in lines:
            if normalized_query in line.casefold():
                results.append(
                    MemorySearchResult(
                        memory_type=entry.memory_type,
                        project_id=entry.project_id,
                        title=entry.title,
                        timestamp=entry.timestamp,
                        path=entry.path,
                        snippet=line.strip(),
                    )
                )
                break

    results.sort(key=lambda result: result.timestamp, reverse=True)
    return results


def _iter_memory_entries(root: Path) -> Iterable[MemoryEntry]:
    yield from _iter_typed_memory(root, Path("memory/sessions"), "session")
    yield from _iter_typed_memory(root, Path("memory/decisions"), "decision")
    yield from _iter_typed_memory(root, Path("memory/project-state"), "project-state")


def _iter_typed_memory(root: Path, relative_dir: Path, default_type: str) -> Iterable[MemoryEntry]:
    memory_dir = root / relative_dir
    if _has_symlink_component(root, relative_dir) or not memory_dir.is_dir():
        return

    try:
        paths = sorted(memory_dir.iterdir(), key=lambda item: item.name)
    except OSError:
        return

    for path in paths:
        if path.is_symlink() or not path.is_file():
            continue
        try:
            if path.stat().st_nlink > 1:
                continue
        except OSError:
            continue
        if path.suffix != ".md":
            continue
        entry = _entry_from_path(path, default_type)
        if entry is not None:
            yield entry


def _has_symlink_component(root: Path, relative: Path) -> bool:
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            return True
    return False


def _entry_from_path(path: Path, default_type: str) -> MemoryEntry | None:
    metadata = parse_front_matter(path)
    if default_type == "project-state" and not metadata:
        return MemoryEntry(
            memory_type="project-state",
            project_id=path.stem,
            title=path.stem,
            timestamp="",
            path=path,
        )

    if not metadata:
        return None

    memory_type = _metadata_string(metadata, "type") or default_type
    project_id = _metadata_string(metadata, "project_id")
    title = _metadata_string(metadata, "title") or path.stem
    timestamp = _metadata_string(metadata, "timestamp")
    if not project_id and default_type == "project-state":
        project_id = path.stem
    if not title:
        title = project_id or path.stem

    return MemoryEntry(
        memory_type=memory_type,
        project_id=project_id,
        title=title,
        timestamp=timestamp,
        path=path,
    )


def _matches_filters(
    entry: MemoryEntry,
    project_id: str | None,
    memory_type: str | None,
) -> bool:
    if project_id is not None and entry.project_id != project_id:
        return False
    if memory_type is not None and entry.memory_type != memory_type:
        return False
    return True


def _metadata_string(metadata: dict[str, object], key: str) -> str:
    value = metadata.get(key)
    return value if isinstance(value, str) else ""


def _parse_scalar(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        try:
            parsed = ast.literal_eval(value)
        except (SyntaxError, ValueError):
            return value[1:-1]
        if isinstance(parsed, str):
            return parsed
    return value
