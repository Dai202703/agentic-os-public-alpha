from dataclasses import dataclass
import json
from pathlib import Path
import re
import subprocess
from typing import Any

from .public_audit import public_audit
from .release_check import release_check
from .release_install_smoke import release_install_smoke


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
    release_install_source: str | Path | None = None,
    release_install_ref: str | None = None,
    release_install_fresh_user_smoke: bool = False,
) -> PublicReleaseGateReport:
    root = Path(repo_root).expanduser().resolve()
    launcher_path = Path(launcher).expanduser().resolve() if launcher else root / "bin/aos"
    steps = [
        _public_audit_step(root, include_history=include_history),
        _release_check_step(root, launcher_path, from_ref=from_ref, to_ref=to_ref),
    ]
    if release_install_source:
        steps.append(
            _release_install_smoke_step(
                root,
                release_install_source,
                release_install_ref,
                fresh_user_smoke_gate=release_install_fresh_user_smoke,
            )
        )
    return PublicReleaseGateReport(repo_root=root, steps=steps)


def infer_previous_release_tag(
    repo_root: str | Path = ".",
    *,
    current_version: str | None = None,
    release_channel: str | None = None,
) -> str | None:
    root = Path(repo_root).expanduser().resolve()
    if current_version is None or release_channel is None:
        try:
            repo_version, repo_channel = _read_repo_version_metadata(root)
        except (OSError, ValueError):
            return None
        current_version = current_version or repo_version
        release_channel = release_channel if release_channel is not None else repo_channel

    current_tuple = _parse_version_tuple(current_version)
    if current_tuple is None:
        return None

    suffix = f"-{release_channel}" if release_channel else ""
    pattern = f"v*{suffix}"
    try:
        completed = subprocess.run(
            ["git", "tag", "--list", pattern],
            cwd=root,
            text=True,
            capture_output=True,
            check=True,
        )
    except (OSError, subprocess.SubprocessError):
        return None

    candidates: list[tuple[tuple[int, int, int], str]] = []
    for line in completed.stdout.splitlines():
        tag = line.strip()
        version_tuple = _parse_release_tag_version(tag, release_channel)
        if version_tuple is not None and version_tuple < current_tuple:
            candidates.append((version_tuple, tag))

    if not candidates:
        return None
    return max(candidates, key=lambda candidate: candidate[0])[1]


def infer_current_release_tag(repo_root: str | Path = ".") -> str | None:
    root = Path(repo_root).expanduser().resolve()
    try:
        version, release_channel = _read_repo_version_metadata(root)
    except (OSError, ValueError):
        return None
    suffix = f"-{release_channel}" if release_channel else ""
    return f"v{version}{suffix}"


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
    resolved_from_ref = from_ref
    from_ref_source = "provided" if from_ref else "missing"
    if resolved_from_ref is None:
        resolved_from_ref = infer_previous_release_tag(root)
        if resolved_from_ref is not None:
            from_ref_source = "inferred"

    try:
        report = release_check(
            root,
            launcher,
            release_manifest_gate=True,
            fresh_user_smoke_gate=True,
            upgrade_smoke=True,
            from_ref=resolved_from_ref,
            to_ref=to_ref,
        )
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        return PublicReleaseGateStep(
            id="release_check",
            status="FAIL",
            message=f"Release check could not run: {error}",
            path=str(root),
            details={
                "from_ref": resolved_from_ref,
                "from_ref_source": from_ref_source,
                "to_ref": to_ref,
                "passed_count": 0,
                "failed_count": 1,
                "steps": [],
                "error": str(error),
            },
            next_action="Run `aos release-check --repo-root . --fresh-user-smoke --upgrade-smoke --json` directly.",
        )
    details = {
        "from_ref": resolved_from_ref,
        "from_ref_source": from_ref_source,
        "to_ref": to_ref,
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
    next_action = getattr(first_failure, "next_action", None) if first_failure else None
    if failure_id == "release_upgrade_smoke" and from_ref_source == "missing":
        next_action = (
            "Fetch full git tags or pass `--from-ref <previous-public-alpha-tag>` "
            "to `aos public-release-gate`."
        )
    return PublicReleaseGateStep(
        id="release_check",
        status="FAIL",
        message=f"Release check failed at {failure_id}: {failure_detail}",
        path=str(root),
        details=details,
        next_action=next_action,
    )


def _release_install_smoke_step(
    root: Path,
    source: str | Path,
    release_ref: str | None,
    *,
    fresh_user_smoke_gate: bool,
) -> PublicReleaseGateStep:
    resolved_ref = release_ref
    ref_source = "provided" if release_ref else "missing"
    if resolved_ref is None:
        resolved_ref = infer_current_release_tag(root)
        if resolved_ref is not None:
            ref_source = "inferred"

    if resolved_ref is None:
        return PublicReleaseGateStep(
            id="release_install_smoke",
            status="FAIL",
            message="Release install smoke requires a release ref but version metadata could not be read.",
            path=str(root),
            details={
                "source": str(source),
                "ref": None,
                "ref_source": ref_source,
                "passed_count": 0,
                "failed_count": 1,
                "fresh_user_smoke_gate": fresh_user_smoke_gate,
                "steps": [],
            },
            next_action="Pass `--release-install-ref <public-release-tag>` or fix src/agentic_os/version.py.",
        )

    try:
        report = release_install_smoke(
            source=source,
            ref=resolved_ref,
            fresh_user_smoke_gate=fresh_user_smoke_gate,
        )
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        return PublicReleaseGateStep(
            id="release_install_smoke",
            status="FAIL",
            message=f"Release install smoke could not run: {error}",
            path=str(root),
            details={
                "source": str(source),
                "ref": resolved_ref,
                "ref_source": ref_source,
                "passed_count": 0,
                "failed_count": 1,
                "fresh_user_smoke_gate": fresh_user_smoke_gate,
                "steps": [],
                "error": str(error),
            },
            next_action="Run `aos release-install-smoke --source <url-or-path> --ref <tag> --json` directly.",
        )

    details = {
        "source": report.source,
        "ref": report.ref,
        "ref_source": ref_source,
        "normalized_ref": report.normalized_ref,
        "expected_tag": report.expected_tag,
        "clone_root": str(report.clone_root),
        "install_dir": str(report.install_dir),
        "expected_version": report.expected_version,
        "installed_version": report.installed_version,
        "passed_count": len(report.passed),
        "failed_count": len(report.failed),
        "fresh_user_smoke_gate": fresh_user_smoke_gate,
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
                "details": getattr(step, "details", None),
            }
            for step in report.steps
        ],
    }
    if report.ok:
        return PublicReleaseGateStep(
            id="release_install_smoke",
            status="PASS",
            message="Release install smoke passed against the published release source.",
            path=str(root),
            details=details,
        )

    first_failure = report.failed[0] if report.failed else None
    failure_detail = first_failure.message if first_failure else "unknown failure"
    failure_id = first_failure.id if first_failure else "unknown"
    next_action = getattr(first_failure, "next_action", None) if first_failure else None
    return PublicReleaseGateStep(
        id="release_install_smoke",
        status="FAIL",
        message=f"Release install smoke failed at {failure_id}: {failure_detail}",
        path=str(root),
        details=details,
        next_action=next_action or "Run `aos release-install-smoke --source <url-or-path> --ref <tag> --json` directly.",
    )


def _read_repo_version_metadata(root: Path) -> tuple[str, str]:
    content = (root / "src/agentic_os/version.py").read_text(encoding="utf-8")
    return (
        _read_python_string_assignment(content, "VERSION"),
        _read_python_string_assignment(content, "RELEASE_CHANNEL"),
    )


def _read_python_string_assignment(content: str, name: str) -> str:
    pattern = rf"(?m)^{re.escape(name)}\s*=\s*[\"']([^\"']+)[\"']\s*$"
    match = re.search(pattern, content)
    if not match:
        raise ValueError(f"Missing {name} in src/agentic_os/version.py")
    return match.group(1)


def _parse_version_tuple(version: str) -> tuple[int, int, int] | None:
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", version)
    if not match:
        return None
    return tuple(int(part) for part in match.groups())


def _parse_release_tag_version(tag: str, release_channel: str) -> tuple[int, int, int] | None:
    suffix = f"-{release_channel}" if release_channel else ""
    if suffix and not tag.endswith(suffix):
        return None
    if suffix:
        version_part = tag.removeprefix("v").removesuffix(suffix)
    else:
        version_part = tag.removeprefix("v")
    return _parse_version_tuple(version_part)
