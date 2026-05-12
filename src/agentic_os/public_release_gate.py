from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
from typing import Any

from .public_audit import public_audit
from .release_check import release_check


@dataclass(frozen=True)
class PublicReleaseGateStep:
    id: str
    status: str
    message: str
    path: str | None = None
    details: dict[str, Any] | None = None
    next_action: str | None = None


@dataclass(frozen=True)
class PublicReleaseGateReport:
    repo_root: Path
    steps: list[PublicReleaseGateStep]

    @property
    def ok(self) -> bool:
        return all(step.status == "PASS" for step in self.steps)

    @property
    def passed(self) -> list[PublicReleaseGateStep]:
        return [step for step in self.steps if step.status == "PASS"]

    @property
    def failed(self) -> list[PublicReleaseGateStep]:
        return [step for step in self.steps if step.status == "FAIL"]


def public_release_gate(
    repo_root: str | Path = ".",
    launcher: str | Path | None = None,
    *,
    from_ref: str | None = None,
    to_ref: str = "HEAD",
    include_history: bool = True,
) -> PublicReleaseGateReport:
    root = Path(repo_root).expanduser().resolve()
    launcher_path = Path(launcher).expanduser().resolve() if launcher else root / "bin/aos"
    steps = [
        _public_audit_step(root, include_history=include_history),
        _release_check_step(root, launcher_path, from_ref=from_ref, to_ref=to_ref),
    ]
    return PublicReleaseGateReport(repo_root=root, steps=steps)


def render_public_release_gate_summary(report: PublicReleaseGateReport) -> str:
    status = "ok" if report.ok else "issues"
    summary = (
        f"AOS public-release-gate {status}: "
        f"{len(report.passed)} passed, "
        f"{len(report.failed)} failed\n"
    )
    if report.failed:
        first_failure = report.failed[0]
        summary += f"first_failure={first_failure.id}: {first_failure.message}\n"
        if first_failure.next_action:
            summary += f"next_action={first_failure.next_action}\n"
    return summary


def render_public_release_gate_json(report: PublicReleaseGateReport) -> str:
    payload = {
        "ok": report.ok,
        "repo_root": str(report.repo_root),
        "passed_count": len(report.passed),
        "failed_count": len(report.failed),
        "steps": [
            {
                "id": step.id,
                "status": step.status,
                "message": step.message,
                "path": step.path,
                "details": step.details,
                "next_action": step.next_action,
            }
            for step in report.steps
        ],
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _public_audit_step(root: Path, *, include_history: bool) -> PublicReleaseGateStep:
    try:
        report = public_audit(root, include_history=include_history)
    except (OSError, subprocess.SubprocessError) as error:
        return PublicReleaseGateStep(
            id="public_audit",
            status="FAIL",
            message=f"Public audit could not run: {error}",
            path=str(root),
            details={"findings_count": 0, "history_scanned": False, "findings": []},
            next_action="Run `aos public-audit --repo-root . --json` directly and inspect git/audit errors.",
        )

    history = "history scanned" if report.history_scanned else "history not scanned"
    details = {
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
    if include_history and not report.history_scanned:
        return PublicReleaseGateStep(
            id="public_audit",
            status="FAIL",
            message=(
                "Public audit history was not scanned; full public-release gate "
                "requires git history coverage."
            ),
            path=str(root),
            details=details,
            next_action=(
                "Run from a git repository, or use `aos public-release-gate --tree-only` "
                "only for development or standalone CI checks."
            ),
        )
    if report.ok:
        return PublicReleaseGateStep(
            id="public_audit",
            status="PASS",
            message=f"Public audit passed; 0 findings, {history}.",
            path=str(root),
            details=details,
        )
    return PublicReleaseGateStep(
        id="public_audit",
        status="FAIL",
        message=f"Public audit failed with {len(report.findings)} findings, {history}.",
        path=str(root),
        details=details,
        next_action="Run `aos public-audit --repo-root . --json` and remove reported findings.",
    )


def _release_check_step(
    root: Path,
    launcher: Path,
    *,
    from_ref: str | None,
    to_ref: str,
) -> PublicReleaseGateStep:
    try:
        report = release_check(
            root,
            launcher,
            release_manifest_gate=True,
            fresh_user_smoke_gate=True,
            upgrade_smoke=True,
            from_ref=from_ref,
            to_ref=to_ref,
        )
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        return PublicReleaseGateStep(
            id="release_check",
            status="FAIL",
            message=f"Release check could not run: {error}",
            path=str(root),
            details={
                "passed_count": 0,
                "failed_count": 1,
                "steps": [],
                "error": str(error),
            },
            next_action="Run `aos release-check --repo-root . --fresh-user-smoke --upgrade-smoke --json` directly.",
        )
    details = {
        "passed_count": len(report.passed),
        "failed_count": len(report.failed),
        "steps": [
            {
                "id": step.id,
                "status": step.status,
                "message": step.message,
                "command": step.command,
                "path": step.path,
                "stdout_tail": step.stdout_tail,
                "stderr_tail": step.stderr_tail,
                "next_action": step.next_action,
            }
            for step in report.steps
        ],
    }
    if report.ok:
        return PublicReleaseGateStep(
            id="release_check",
            status="PASS",
            message="Release check passed with manifest, fresh-user smoke, and upgrade smoke.",
            path=str(root),
            details=details,
        )

    first_failure = report.failed[0] if report.failed else None
    failure_detail = first_failure.message if first_failure else "unknown failure"
    failure_id = first_failure.id if first_failure else "unknown"
    return PublicReleaseGateStep(
        id="release_check",
        status="FAIL",
        message=f"Release check failed at {failure_id}: {failure_detail}",
        path=str(root),
        details=details,
        next_action=getattr(first_failure, "next_action", None) if first_failure else None,
    )
