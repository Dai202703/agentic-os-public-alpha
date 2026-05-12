from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re


MANIFEST_NAME = "public-release-manifest.json"
IGNORED_NAMES = {MANIFEST_NAME, ".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
IGNORED_SUFFIXES = {".pyc", ".pyo"}
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class ReleaseManifestIssue:
    code: str
    path: str | None
    message: str


@dataclass(frozen=True)
class ReleaseManifestReport:
    repo_root: Path
    manifest_path: Path
    files: list[str]
    issues: list[ReleaseManifestIssue]

    @property
    def ok(self) -> bool:
        return not self.issues

    @property
    def files_count(self) -> int:
        return len(self.files)


def release_manifest_check(repo_root: str | Path = ".") -> ReleaseManifestReport:
    root = Path(repo_root).expanduser().resolve()
    manifest_path = root / MANIFEST_NAME
    actual_files = _regular_files(root)
    issues: list[ReleaseManifestIssue] = []

    if not manifest_path.is_file():
        return ReleaseManifestReport(
            repo_root=root,
            manifest_path=manifest_path,
            files=actual_files,
            issues=[
                ReleaseManifestIssue(
                    code="MANIFEST_MISSING",
                    path=MANIFEST_NAME,
                    message="public-release-manifest.json is missing.",
                )
            ],
        )

    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        return ReleaseManifestReport(
            repo_root=root,
            manifest_path=manifest_path,
            files=actual_files,
            issues=[
                ReleaseManifestIssue(
                    code="MANIFEST_INVALID_JSON",
                    path=MANIFEST_NAME,
                    message=f"Manifest JSON is invalid: {error}",
                )
            ],
        )

    manifest_files = _manifest_files(payload, issues)
    checksums = _manifest_checksums(payload, issues)
    if issues:
        return ReleaseManifestReport(root, manifest_path, actual_files, issues)

    actual_set = set(actual_files)
    manifest_set = set(manifest_files)
    checksum_set = set(checksums)

    for relative in sorted(manifest_set - actual_set):
        issues.append(
            ReleaseManifestIssue(
                code="MANIFEST_FILE_MISSING",
                path=relative,
                message=f"Manifest lists a file that is missing: {relative}",
            )
        )

    for relative in sorted(actual_set - manifest_set):
        issues.append(
            ReleaseManifestIssue(
                code="MANIFEST_FILE_UNLISTED",
                path=relative,
                message=f"Repository contains an unlisted release file: {relative}",
            )
        )

    for relative in sorted(manifest_set - checksum_set):
        issues.append(
            ReleaseManifestIssue(
                code="CHECKSUM_MISSING",
                path=relative,
                message=f"Manifest is missing a SHA-256 checksum for {relative}.",
            )
        )

    for relative in sorted(checksum_set - manifest_set):
        issues.append(
            ReleaseManifestIssue(
                code="CHECKSUM_FILE_UNLISTED",
                path=relative,
                message=f"Manifest has a checksum for an unlisted file: {relative}",
            )
        )

    for relative in sorted(manifest_set & checksum_set & actual_set):
        expected = checksums[relative]
        if not SHA256_PATTERN.match(expected):
            issues.append(
                ReleaseManifestIssue(
                    code="CHECKSUM_INVALID",
                    path=relative,
                    message=f"Manifest checksum for {relative} is not a lowercase SHA-256 digest.",
                )
            )
            continue
        actual = hashlib.sha256((root / relative).read_bytes()).hexdigest()
        if actual != expected:
            issues.append(
                ReleaseManifestIssue(
                    code="CHECKSUM_MISMATCH",
                    path=relative,
                    message=f"Manifest checksum for {relative} is stale.",
                )
            )

    return ReleaseManifestReport(root, manifest_path, actual_files, issues)


def _manifest_files(payload: object, issues: list[ReleaseManifestIssue]) -> list[str]:
    if not isinstance(payload, dict):
        issues.append(
            ReleaseManifestIssue(
                code="MANIFEST_INVALID",
                path=MANIFEST_NAME,
                message="Manifest root must be a JSON object.",
            )
        )
        return []

    files = payload.get("files")
    if not isinstance(files, list) or not all(isinstance(item, str) for item in files):
        issues.append(
            ReleaseManifestIssue(
                code="MANIFEST_INVALID_FILES",
                path=MANIFEST_NAME,
                message="Manifest files must be a list of relative paths.",
            )
        )
        return []

    safe_files: list[str] = []
    for relative in files:
        if not _safe_relative_path(relative):
            issues.append(
                ReleaseManifestIssue(
                    code="MANIFEST_INVALID_PATH",
                    path=relative,
                    message=f"Manifest path is not a safe relative path: {relative}",
                )
            )
        else:
            safe_files.append(relative)
    return safe_files


def _manifest_checksums(payload: object, issues: list[ReleaseManifestIssue]) -> dict[str, str]:
    if not isinstance(payload, dict):
        return {}

    checksums = payload.get("sha256")
    if not isinstance(checksums, dict) or not all(
        isinstance(key, str) and isinstance(value, str) for key, value in checksums.items()
    ):
        issues.append(
            ReleaseManifestIssue(
                code="MANIFEST_INVALID_CHECKSUMS",
                path=MANIFEST_NAME,
                message="Manifest sha256 must be an object of relative paths to digest strings.",
            )
        )
        return {}

    safe_checksums: dict[str, str] = {}
    for relative, digest in checksums.items():
        if not _safe_relative_path(relative):
            issues.append(
                ReleaseManifestIssue(
                    code="MANIFEST_INVALID_PATH",
                    path=relative,
                    message=f"Manifest checksum path is not a safe relative path: {relative}",
                )
            )
        else:
            safe_checksums[relative] = digest
    return safe_checksums


def _regular_files(root: Path) -> list[str]:
    return sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and not _ignored(path.relative_to(root))
    )


def _ignored(relative: Path) -> bool:
    return (
        any(part in IGNORED_NAMES for part in relative.parts)
        or relative.suffix in IGNORED_SUFFIXES
    )


def _safe_relative_path(value: str) -> bool:
    path = Path(value)
    return bool(value) and not path.is_absolute() and ".." not in path.parts
