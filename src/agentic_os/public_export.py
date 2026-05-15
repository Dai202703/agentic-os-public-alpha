from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import os
import shutil


PUBLIC_EXPORT_PATHS = [
    ".gitignore",
    ".github",
    "bin",
    "docs",
    "scripts",
    "src",
    "tests",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "LICENSE",
    "README.md",
    "SECURITY.md",
    "pyproject.toml",
]
EXCLUDED_NAMES = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
DISALLOWED_PUBLIC_EXTENSIONS = {
    ".7z",
    ".db",
    ".docx",
    ".gz",
    ".key",
    ".p12",
    ".pdf",
    ".pem",
    ".sqlite",
    ".tar",
    ".zip",
}


@dataclass(frozen=True)
class PublicExportManifest:
    output_root: Path
    files: list[str]
    checksums: dict[str, str]

    @property
    def ok(self) -> bool:
        return True


def public_export(
    repo_root: str | Path = ".",
    output_root: str | Path = "/tmp/agentic-os-public",
    force: bool = False,
) -> PublicExportManifest:
    source = Path(repo_root).expanduser().resolve()
    output = Path(output_root).expanduser().resolve()
    if output.exists() and any(output.iterdir()):
        if not force:
            raise ValueError(f"Output directory is not empty: {output}")
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)
    _preflight_public_export(source)

    for relative in PUBLIC_EXPORT_PATHS:
        source_path = source / relative
        if not source_path.exists():
            continue
        target_path = output / relative
        if source_path.is_dir():
            shutil.copytree(
                source_path,
                target_path,
                ignore=shutil.ignore_patterns(*EXCLUDED_NAMES),
                dirs_exist_ok=True,
            )
        elif source_path.is_file():
            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, target_path)

    files = _regular_files(output)
    checksums = _file_checksums(output, files)
    _write_manifest(output, files, checksums)
    return PublicExportManifest(output, files, checksums)


def render_public_export_json(manifest: PublicExportManifest) -> str:
    payload = {
        "ok": manifest.ok,
        "output_root": str(manifest.output_root),
        "files_count": len(manifest.files),
        "files": manifest.files,
        "sha256": manifest.checksums,
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def render_public_export_summary(manifest: PublicExportManifest) -> str:
    return f"AOS public-export ok: {len(manifest.files)} files written to {manifest.output_root}\n"


def _regular_files(root: Path) -> list[str]:
    return sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and path.name != "public-release-manifest.json"
    )


def _preflight_public_export(source: Path) -> None:
    for relative in PUBLIC_EXPORT_PATHS:
        source_path = source / relative
        if not source_path.exists() and not source_path.is_symlink():
            continue
        _reject_unsafe_export_path(source, source_path)


def _reject_unsafe_export_path(source: Path, path: Path) -> None:
    if path.is_symlink():
        raise ValueError(f"Symlink is not allowed in public export: {_display_relative(source, path)}")
    if path.is_file():
        _reject_unsafe_file_content(source, path)
        return
    if not path.is_dir():
        return

    for current_root, dirnames, filenames in os.walk(path):
        current_path = Path(current_root)
        dirnames[:] = [
            dirname
            for dirname in dirnames
            if dirname not in EXCLUDED_NAMES
        ]
        for dirname in list(dirnames):
            child = current_path / dirname
            if child.is_symlink():
                raise ValueError(f"Symlink is not allowed in public export: {_display_relative(source, child)}")
        for filename in filenames:
            child = current_path / filename
            if child.is_symlink():
                raise ValueError(f"Symlink is not allowed in public export: {_display_relative(source, child)}")
            if child.is_file():
                _reject_unsafe_file_content(source, child)


def _reject_unsafe_file_content(source: Path, path: Path) -> None:
    if path.suffix.lower() in DISALLOWED_PUBLIC_EXTENSIONS:
        raise ValueError(f"Risky file type is not allowed in public export: {_display_relative(source, path)}")
    content = path.read_bytes()
    if b"\x00" in content:
        raise ValueError(f"Binary or non-UTF-8 file is not allowed in public export: {_display_relative(source, path)}")
    try:
        content.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError(
            f"Binary or non-UTF-8 file is not allowed in public export: {_display_relative(source, path)}"
        ) from error


def _display_relative(source: Path, path: Path) -> str:
    try:
        return path.relative_to(source).as_posix()
    except ValueError:
        return str(path)


def _file_checksums(root: Path, files: list[str]) -> dict[str, str]:
    return {
        relative: hashlib.sha256((root / relative).read_bytes()).hexdigest()
        for relative in files
    }


def _write_manifest(output: Path, files: list[str], checksums: dict[str, str]) -> None:
    (output / "public-release-manifest.json").write_text(
        json.dumps({"files": files, "sha256": checksums}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
