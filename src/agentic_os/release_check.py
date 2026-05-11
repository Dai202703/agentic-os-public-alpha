from dataclasses import dataclass
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from typing import Sequence

from .distribution import distribution_check
from .version import get_release_tag


@dataclass(frozen=True)
class ReleaseCheckStep:
    id: str
    status: str
    message: str
    command: str | None = None
    path: str | None = None
    stdout_tail: str | None = None
    stderr_tail: str | None = None


@dataclass(frozen=True)
class ReleaseCheckReport:
    repo_root: Path
    steps: list[ReleaseCheckStep]

    @property
    def ok(self) -> bool:
        return all(step.status == "PASS" for step in self.steps)

    @property
    def passed(self) -> list[ReleaseCheckStep]:
        return [step for step in self.steps if step.status == "PASS"]

    @property
    def failed(self) -> list[ReleaseCheckStep]:
        return [step for step in self.steps if step.status == "FAIL"]


def release_check(repo_root: str | Path = ".", launcher: str | Path | None = None) -> ReleaseCheckReport:
    root = Path(repo_root).expanduser().resolve()
    launcher_path = Path(launcher).expanduser().resolve() if launcher else root / "bin/aos"
    steps = [
        _version_consistency_step(root),
        _run_command_step(
            "unit_tests",
            [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
            root,
            "Unit test suite passed.",
        ),
        _run_command_step(
            "readiness_smoke",
            [
                sys.executable,
                str(root / "scripts/readiness_smoke.py"),
                "--launcher",
                str(launcher_path),
                "--json",
            ],
            root,
            "Repo-contained readiness smoke passed.",
        ),
        _distribution_step(root),
        _install_manager_dry_run_step(root, launcher_path),
    ]
    return ReleaseCheckReport(root, steps)


def render_release_check_summary(report: ReleaseCheckReport) -> str:
    status = "ok" if report.ok else "issues"
    return (
        f"AOS release-check {status}: "
        f"{len(report.passed)} passed, "
        f"{len(report.failed)} failed\n"
    )


def render_release_check_json(report: ReleaseCheckReport) -> str:
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
                "command": step.command,
                "path": step.path,
                "stdout_tail": step.stdout_tail,
                "stderr_tail": step.stderr_tail,
            }
            for step in report.steps
        ],
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _distribution_step(root: Path) -> ReleaseCheckStep:
    report = distribution_check(root)
    if report.ok:
        return ReleaseCheckStep(
            id="distribution_check",
            status="PASS",
            message=f"Distribution privacy gate passed; {report.scanned_files_count} files scanned.",
            path=str(root),
        )
    return ReleaseCheckStep(
        id="distribution_check",
        status="FAIL",
        message=f"Distribution privacy gate failed with {len(report.issues)} findings.",
        path=str(root),
    )


def _version_consistency_step(root: Path) -> ReleaseCheckStep:
    try:
        code_version, release_channel = _read_version_metadata(root)
        package_version = _read_pyproject_version(root)
        changelog_tag = _read_top_changelog_tag(root)
    except (OSError, ValueError) as error:
        return ReleaseCheckStep(
            id="version_consistency",
            status="FAIL",
            message=f"Version metadata check failed: {error}",
            path=str(root),
        )

    expected_tag = get_release_tag(code_version, release_channel)
    findings: list[str] = []
    if package_version != code_version:
        findings.append(f"pyproject version is {package_version}; expected {code_version}")
    if changelog_tag != expected_tag:
        findings.append(f"CHANGELOG top release is {changelog_tag}; expected {expected_tag}")

    if findings:
        return ReleaseCheckStep(
            id="version_consistency",
            status="FAIL",
            message="Version metadata mismatch: " + "; ".join(findings) + ".",
            path=str(root),
        )

    return ReleaseCheckStep(
        id="version_consistency",
        status="PASS",
        message=f"Version metadata is consistent: {expected_tag}.",
        path=str(root),
    )


def _read_version_metadata(root: Path) -> tuple[str, str]:
    content = (root / "src/agentic_os/version.py").read_text(encoding="utf-8")
    version = _read_python_string_assignment(content, "VERSION")
    release_channel = _read_python_string_assignment(content, "RELEASE_CHANNEL")
    return version, release_channel


def _read_python_string_assignment(content: str, name: str) -> str:
    pattern = rf"(?m)^{re.escape(name)}\s*=\s*[\"']([^\"']+)[\"']\s*$"
    match = re.search(pattern, content)
    if not match:
        raise ValueError(f"Missing {name} in src/agentic_os/version.py")
    return match.group(1)


def _read_pyproject_version(root: Path) -> str:
    content = (root / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'(?m)^version\s*=\s*"([^"]+)"\s*$', content)
    if not match:
        raise ValueError("Missing project version in pyproject.toml")
    return match.group(1)


def _read_top_changelog_tag(root: Path) -> str:
    content = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    match = re.search(r"(?m)^##\s+(v[^\s]+)\s*$", content)
    if not match:
        raise ValueError("Missing top release heading in CHANGELOG.md")
    return match.group(1)


def _install_manager_dry_run_step(root: Path, launcher: Path) -> ReleaseCheckStep:
    manager = root / "scripts/manage_global_aos.py"
    commands: list[list[str]] = []
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        install_dir = temp_path / "bin"
        state_file = temp_path / "state.json"
        commands.extend(
            [
                [
                    sys.executable,
                    str(manager),
                    "status",
                    "--install-dir",
                    str(install_dir),
                    "--state-file",
                    str(state_file),
                ],
                [
                    sys.executable,
                    str(manager),
                    "install",
                    "--launcher",
                    str(launcher),
                    "--install-dir",
                    str(install_dir),
                    "--state-file",
                    str(state_file),
                ],
                [
                    sys.executable,
                    str(manager),
                    "update",
                    "--launcher",
                    str(launcher),
                    "--install-dir",
                    str(install_dir),
                    "--state-file",
                    str(state_file),
                ],
                [
                    sys.executable,
                    str(manager),
                    "rollback",
                    "--install-dir",
                    str(install_dir),
                    "--state-file",
                    str(state_file),
                ],
            ]
        )
        for command in commands:
            completed = _run_command(command, root)
            if completed.returncode != 0:
                return _failed_step("install_manager_dry_run", command, root, completed)

    return ReleaseCheckStep(
        id="install_manager_dry_run",
        status="PASS",
        message="Install manager dry-run passed: status, install, update, rollback.",
        path=str(root),
    )


def _run_command_step(
    step_id: str,
    command: Sequence[str],
    cwd: Path,
    success_message: str,
) -> ReleaseCheckStep:
    completed = _run_command(command, cwd)
    if completed.returncode != 0:
        return _failed_step(step_id, command, cwd, completed)
    return ReleaseCheckStep(
        id=step_id,
        status="PASS",
        message=success_message,
        command=_format_command(command),
        path=str(cwd),
        stdout_tail=_tail(completed.stdout),
        stderr_tail=_tail(completed.stderr),
    )


def _run_command(command: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(part) for part in command],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )


def _failed_step(
    step_id: str,
    command: Sequence[str],
    cwd: Path,
    completed: subprocess.CompletedProcess[str],
) -> ReleaseCheckStep:
    return ReleaseCheckStep(
        id=step_id,
        status="FAIL",
        message=f"Command failed with exit code {completed.returncode}.",
        command=_format_command(command),
        path=str(cwd),
        stdout_tail=_tail(completed.stdout),
        stderr_tail=_tail(completed.stderr),
    )


def _format_command(command: Sequence[str]) -> str:
    return " ".join(str(part) for part in command)


def _tail(value: str | None, limit: int = 1200) -> str | None:
    if not value:
        return None
    return value[-limit:]
