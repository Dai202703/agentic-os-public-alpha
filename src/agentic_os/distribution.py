from dataclasses import dataclass
import json
import os
from pathlib import Path
import re

from .security import (
    PRIVATE_MEMORY_REFERENCE_PATTERN,
    SECRET_PATTERN,
    SENSITIVE_FILENAMES,
    should_scan_private_memory_reference,
)


GENERATED_PROVIDER_OUTPUTS = {
    Path("AGENTS.md"),
    Path("CLAUDE.md"),
    Path("GEMINI.md"),
    Path(".agentic-os/chatgpt-project-instructions.md"),
}
PRIVATE_OS_HOME_PATHS = {
    Path(".agentic-os"),
    Path("core"),
    Path("memory"),
    Path("projects"),
    Path("providers"),
}
SKIPPED_DIRECTORIES = {".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
CONTENT_SCAN_SKIPPED_DIRECTORIES = {"tests"}
CONTENT_SCAN_SKIPPED_FILES = {
    Path("src/agentic_os/distribution.py"),
    Path("src/agentic_os/security.py"),
}
DISTRIBUTION_LOCAL_PATH_PATTERN = re.compile(
    r"(?<![\w.-])(?:/Users/|/private/var/|/var/folders/)[^\s'\"`)]+"
)


@dataclass(frozen=True)
class DistributionIssue:
    code: str
    path: str
    message: str
    line: int | None = None


@dataclass(frozen=True)
class DistributionReport:
    repo_root: Path
    issues: list[DistributionIssue]
    scanned_files_count: int

    @property
    def ok(self) -> bool:
        return not self.issues


def distribution_check(repo_root: str | Path = ".") -> DistributionReport:
    root = Path(repo_root).expanduser().resolve()
    issues: list[DistributionIssue] = []

    for relative in sorted(PRIVATE_OS_HOME_PATHS):
        path = root / relative
        if path.exists() or path.is_symlink():
            issues.append(
                DistributionIssue(
                    "PRIVATE_OS_HOME_PATH",
                    str(path),
                    f"Private OS home path must not be part of a shareable package: {relative.as_posix()}",
                )
            )

    for relative in sorted(GENERATED_PROVIDER_OUTPUTS):
        path = root / relative
        if path.exists() or path.is_symlink():
            issues.append(
                DistributionIssue(
                    "GENERATED_PROVIDER_OUTPUT",
                    str(path),
                    f"Generated provider output must not be part of a shareable package: {relative.as_posix()}",
                )
            )

    scanned_files = _distribution_regular_files(root)
    issues.extend(_content_issues(root, scanned_files))
    return DistributionReport(root, issues, len(scanned_files))


def render_distribution_check_summary(report: DistributionReport) -> str:
    status = "ok" if report.ok else "issues"
    return (
        f"AOS distribution-check {status}: "
        f"{len(report.issues)} findings, "
        f"{report.scanned_files_count} files scanned\n"
    )


def render_distribution_check_json(report: DistributionReport) -> str:
    payload = {
        "ok": report.ok,
        "repo_root": str(report.repo_root),
        "findings_count": len(report.issues),
        "scanned_files_count": report.scanned_files_count,
        "issues": [
            {
                "code": issue.code,
                "path": issue.path,
                "message": issue.message,
                "line": issue.line,
            }
            for issue in report.issues
        ],
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _content_issues(root: Path, paths: list[Path]) -> list[DistributionIssue]:
    issues: list[DistributionIssue] = []
    for path in paths:
        if _skip_content_scan(root, path):
            continue
        if path.name in SENSITIVE_FILENAMES:
            issues.append(
                DistributionIssue(
                    "SENSITIVE_FILENAME",
                    str(path),
                    f"Sensitive filename detected: {path.name}",
                )
            )

        try:
            content = path.read_bytes()
        except OSError:
            continue
        if b"\x00" in content:
            continue
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            continue

        for line_number, line in enumerate(text.splitlines(), start=1):
            if SECRET_PATTERN.search(line):
                issues.append(
                    DistributionIssue(
                        "SECRET_PATTERN",
                        str(path),
                        "Potential secret pattern detected",
                        line_number,
                    )
                )
            if DISTRIBUTION_LOCAL_PATH_PATTERN.search(line):
                issues.append(
                    DistributionIssue(
                        "LOCAL_PATH_PATTERN",
                        str(path),
                        "Local filesystem path pattern detected",
                        line_number,
                    )
                )
            if (
                should_scan_private_memory_reference(path)
                and PRIVATE_MEMORY_REFERENCE_PATTERN.search(line)
            ):
                issues.append(
                    DistributionIssue(
                        "PRIVATE_MEMORY_REFERENCE",
                        str(path),
                        "Private project memory reference detected",
                        line_number,
                    )
                )
    return issues


def _skip_content_scan(root: Path, path: Path) -> bool:
    try:
        relative = path.relative_to(root)
    except ValueError:
        return False
    if relative in CONTENT_SCAN_SKIPPED_FILES:
        return True
    return any(part in CONTENT_SCAN_SKIPPED_DIRECTORIES for part in relative.parts)


def _distribution_regular_files(root: Path) -> list[Path]:
    if root.is_symlink() or not root.exists():
        return []
    if root.is_file():
        return [root]

    files: list[Path] = []
    for current_root, dirnames, filenames in os.walk(root):
        current_path = Path(current_root)
        dirnames[:] = [
            dirname
            for dirname in dirnames
            if dirname not in SKIPPED_DIRECTORIES and not (current_path / dirname).is_symlink()
        ]
        for filename in filenames:
            child = current_path / filename
            if child.is_symlink() or not child.is_file():
                continue
            files.append(child)
    return sorted(files)
