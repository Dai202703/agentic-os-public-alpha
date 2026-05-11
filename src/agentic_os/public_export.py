from dataclasses import dataclass
import json
from pathlib import Path
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


@dataclass(frozen=True)
class PublicExportManifest:
    output_root: Path
    files: list[str]

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
    _write_manifest(output, files)
    return PublicExportManifest(output, files)


def render_public_export_json(manifest: PublicExportManifest) -> str:
    payload = {
        "ok": manifest.ok,
        "output_root": str(manifest.output_root),
        "files_count": len(manifest.files),
        "files": manifest.files,
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


def _write_manifest(output: Path, files: list[str]) -> None:
    (output / "public-release-manifest.json").write_text(
        json.dumps({"files": files}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
