from dataclasses import dataclass
import json
from pathlib import Path
import subprocess

from .distribution import (
    CONTENT_SCAN_SKIPPED_DIRECTORIES,
    CONTENT_SCAN_SKIPPED_FILES,
    DISTRIBUTION_LOCAL_PATH_PATTERN,
    distribution_check,
)
from .security import (
    PRIVATE_MEMORY_REFERENCE_PATTERN,
    SECRET_PATTERN,
    SENSITIVE_FILENAMES,
    should_scan_private_memory_reference,
)


@dataclass(frozen=True)
class PublicAuditFinding:
    source: str
    code: str
    path: str
    message: str
    line: int | None = None
    commit: str | None = None


@dataclass(frozen=True)
class PublicAuditReport:
    repo_root: Path
    findings: list[PublicAuditFinding]
    history_scanned: bool

    @property
    def ok(self) -> bool:
        return not self.findings


def public_audit(repo_root: str | Path = ".", include_history: bool = True) -> PublicAuditReport:
    root = Path(repo_root).expanduser().resolve()
    findings: list[PublicAuditFinding] = []

    tree_report = distribution_check(root)
    findings.extend(
        PublicAuditFinding(
            source="tree",
            code=issue.code,
            path=issue.path,
            message=issue.message,
            line=issue.line,
        )
        for issue in tree_report.issues
    )

    history_scanned = False
    if include_history:
        history_findings, history_scanned = _history_findings(root)
        findings.extend(history_findings)
    return PublicAuditReport(root, findings, history_scanned)


def render_public_audit_summary(report: PublicAuditReport) -> str:
    status = "ok" if report.ok else "issues"
    history = "history scanned" if report.history_scanned else "history not scanned"
    return f"AOS public-audit {status}: {len(report.findings)} findings, {history}\n"


def render_public_audit_json(report: PublicAuditReport) -> str:
    payload = {
        "ok": report.ok,
        "repo_root": str(report.repo_root),
        "findings_count": len(report.findings),
        "history_scanned": report.history_scanned,
        "findings": [
            {
                "source": finding.source,
                "code": finding.code,
                "path": finding.path,
                "message": finding.message,
                "line": finding.line,
                "commit": finding.commit,
            }
            for finding in report.findings
        ],
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _history_findings(root: Path) -> tuple[list[PublicAuditFinding], bool]:
    if not _is_git_repository(root):
        return [], False

    commits = _git_lines(root, ["rev-list", "--all"])
    findings: list[PublicAuditFinding] = []
    for commit in commits:
        for relative in _git_lines(root, ["ls-tree", "-r", "--name-only", commit]):
            relative_path = Path(relative)
            if _skip_history_scan(relative_path):
                continue
            if relative_path.name in SENSITIVE_FILENAMES:
                findings.append(
                    PublicAuditFinding(
                        source="history",
                        code="SENSITIVE_FILENAME",
                        path=relative,
                        message=f"Sensitive filename detected in git history: {relative_path.name}",
                        commit=commit,
                    )
                )
            blob = _git_blob(root, commit, relative)
            if blob is None:
                continue
            if b"\x00" in blob:
                continue
            try:
                text = blob.decode("utf-8")
            except UnicodeDecodeError:
                continue
            for line_number, line in enumerate(text.splitlines(), start=1):
                if SECRET_PATTERN.search(line):
                    findings.append(
                        PublicAuditFinding(
                            source="history",
                            code="SECRET_PATTERN",
                            path=relative,
                            message="Potential secret pattern detected in git history",
                            line=line_number,
                            commit=commit,
                        )
                    )
                if DISTRIBUTION_LOCAL_PATH_PATTERN.search(line):
                    findings.append(
                        PublicAuditFinding(
                            source="history",
                            code="LOCAL_PATH_PATTERN",
                            path=relative,
                            message="Local filesystem path pattern detected in git history",
                            line=line_number,
                            commit=commit,
                        )
                    )
                if (
                    should_scan_private_memory_reference(relative_path)
                    and PRIVATE_MEMORY_REFERENCE_PATTERN.search(line)
                ):
                    findings.append(
                        PublicAuditFinding(
                            source="history",
                            code="PRIVATE_MEMORY_REFERENCE",
                            path=relative,
                            message="Private project memory reference detected in git history",
                            line=line_number,
                            commit=commit,
                        )
                    )
    return findings, True


def _is_git_repository(root: Path) -> bool:
    completed = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    return completed.returncode == 0 and completed.stdout.strip() == "true"


def _git_lines(root: Path, args: list[str]) -> list[str]:
    completed = subprocess.run(
        ["git", *args],
        cwd=root,
        text=True,
        capture_output=True,
        check=True,
    )
    return [line for line in completed.stdout.splitlines() if line.strip()]


def _git_blob(root: Path, commit: str, relative: str) -> bytes | None:
    completed = subprocess.run(
        ["git", "show", f"{commit}:{relative}"],
        cwd=root,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        return None
    return completed.stdout


def _skip_history_scan(relative: Path) -> bool:
    if relative in CONTENT_SCAN_SKIPPED_FILES:
        return True
    return any(part in CONTENT_SCAN_SKIPPED_DIRECTORIES for part in relative.parts)
