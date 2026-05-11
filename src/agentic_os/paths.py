import os
from pathlib import Path


DEFAULT_OS_HOME = Path.home() / ".agentic-os"


def resolve_os_home(value: str | os.PathLike[str] | None = None) -> Path:
    raw = value or os.environ.get("AGENTIC_OS_HOME") or DEFAULT_OS_HOME
    return Path(raw).expanduser().resolve()


def resolve_project_root(value: str | os.PathLike[str]) -> Path:
    root = Path(value).expanduser()
    reject_project_root_symlink_components(root)
    return root.resolve()


def ensure_managed_directory(os_home: Path, relative: str | Path) -> Path:
    root = os_home.expanduser().resolve()
    relative_path = validate_relative_path(relative)
    target = root / relative_path
    reject_symlink_components(root, relative_path)
    ensure_inside(root, target, "Managed directory")
    target.mkdir(parents=True, exist_ok=True)
    if not target.is_dir():
        raise NotADirectoryError(target)
    ensure_inside(root, target, "Managed directory")
    return target


def ensure_managed_file(os_home: Path, relative: str | Path) -> Path:
    root = os_home.expanduser().resolve()
    relative_path = validate_relative_path(relative)
    ensure_managed_directory(root, relative_path.parent)
    target = root / relative_path
    if target.is_symlink():
        raise ValueError(f"Managed file may not be a symlink: {relative_path}")
    if target.is_file() and target.stat().st_nlink > 1:
        raise ValueError(f"Managed file may not be hardlinked: {relative_path}")
    ensure_inside(root, target, "Managed file")
    return target


def ensure_project_directory(project_root: Path, relative: str | Path) -> Path:
    base = project_root.expanduser()
    root = base.resolve()
    relative_path = validate_relative_path(relative)
    target = base / relative_path
    reject_symlink_components(root, relative_path)
    ensure_inside(root, target, "Project directory")
    target.mkdir(parents=True, exist_ok=True)
    if not target.is_dir():
        raise NotADirectoryError(target)
    ensure_inside(root, target, "Project directory")
    return target


def ensure_project_file(project_root: Path, relative: str | Path) -> Path:
    base = project_root.expanduser()
    root = base.resolve()
    relative_path = validate_relative_path(relative)
    ensure_project_directory(root, relative_path.parent)
    target = base / relative_path
    if target.is_symlink():
        raise ValueError(f"Project file may not be a symlink: {relative_path}")
    if target.is_file() and target.stat().st_nlink > 1:
        raise ValueError(f"Project file may not be hardlinked: {relative_path}")
    ensure_inside(root, target, "Project file")
    return target


def ensure_readable_file(root: Path, relative: str | Path, label: str) -> Path:
    root = root.expanduser().resolve()
    relative_path = validate_relative_path(relative)
    target = root / relative_path
    reject_symlink_components(root, relative_path.parent)
    ensure_inside(root, target, label)
    if target.is_symlink():
        raise ValueError(f"{label} may not be a symlink: {relative_path}")
    if not target.is_file():
        raise FileNotFoundError(target)
    if target.stat().st_nlink > 1:
        raise ValueError(f"{label} may not be hardlinked: {relative_path}")
    return target


def validate_relative_path(relative: str | Path) -> Path:
    relative_path = Path(relative)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise ValueError(f"Managed path must be relative to Agentic OS home: {relative}")
    return relative_path


def reject_symlink_components(root: Path, relative: Path) -> None:
    if relative == Path("."):
        return

    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"Managed path may not contain symlinks: {relative}")


def reject_project_root_symlink_components(root: Path) -> None:
    raw_root = root if root.is_absolute() else Path.cwd() / root
    current = Path(raw_root.anchor)

    for part in raw_root.parts[1:]:
        if part == ".":
            continue
        if part == "..":
            current = current.parent
            continue

        current = current / part
        if current.is_symlink() and current.parent != Path(raw_root.anchor):
            raise ValueError(f"Project root may not contain symlinks: {root}")


def ensure_inside(root: Path, target: Path, label: str) -> None:
    if not target.resolve().is_relative_to(root):
        raise ValueError(f"{label} escapes Agentic OS home: {target}")
