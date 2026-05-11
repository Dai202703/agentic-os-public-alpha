from dataclasses import dataclass
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from typing import Sequence


@dataclass(frozen=True)
class ReleaseUpgradeSmokeStep:
    id: str
    status: str
    message: str
    command: str | None = None
    path: str | None = None
    stdout_tail: str | None = None
    stderr_tail: str | None = None


@dataclass(frozen=True)
class ReleaseUpgradeSmokeReport:
    repo_root: Path
    from_ref: str
    to_ref: str
    install_dir: Path
    previous_version: dict[str, str]
    current_version: dict[str, str]
    steps: list[ReleaseUpgradeSmokeStep]

    @property
    def ok(self) -> bool:
        return all(step.status == "PASS" for step in self.steps)

    @property
    def passed(self) -> list[ReleaseUpgradeSmokeStep]:
        return [step for step in self.steps if step.status == "PASS"]

    @property
    def failed(self) -> list[ReleaseUpgradeSmokeStep]:
        return [step for step in self.steps if step.status == "FAIL"]


def release_upgrade_smoke(
    repo_root: str | Path = ".",
    from_ref: str | None = None,
    to_ref: str = "HEAD",
) -> ReleaseUpgradeSmokeReport:
    if not from_ref:
        raise ValueError("from_ref is required")

    root = Path(repo_root).expanduser().resolve()
    if not (root / ".git").exists():
        raise ValueError(f"release-upgrade-smoke requires a git repository: {root}")

    steps: list[ReleaseUpgradeSmokeStep] = []
    previous_version: dict[str, str] = {}
    current_version: dict[str, str] = {}

    with tempfile.TemporaryDirectory(prefix="aos-release-upgrade-") as temp_dir:
        workspace = Path(temp_dir)
        previous_root = workspace / "previous"
        current_root = workspace / "current"
        install_dir = workspace / "install/bin"
        state_file = workspace / "install/state.json"
        active = install_dir / "aos"

        for step_id, target, ref in (
            ("checkout_previous_ref", previous_root, from_ref),
            ("checkout_current_ref", current_root, to_ref),
        ):
            step = _checkout_ref(root, target, ref, step_id)
            steps.append(step)
            if step.status == "FAIL":
                return _report(root, from_ref, to_ref, install_dir, previous_version, current_version, steps)

        try:
            previous_version = _read_version_info(previous_root)
            current_version = _read_version_info(current_root)
        except (OSError, ValueError) as error:
            steps.append(
                ReleaseUpgradeSmokeStep(
                    id="read_version_metadata",
                    status="FAIL",
                    message=f"Could not read release version metadata: {error}",
                    path=str(workspace),
                )
            )
            return _report(root, from_ref, to_ref, install_dir, previous_version, current_version, steps)

        previous_launcher = previous_root / "bin/aos"
        current_launcher = current_root / "bin/aos"
        previous_manager = previous_root / "scripts/manage_global_aos.py"
        current_manager = current_root / "scripts/manage_global_aos.py"

        install_step = _manager_step(
            "install_previous",
            previous_manager,
            "install",
            previous_launcher,
            install_dir,
            state_file,
            previous_root,
            f"Installed previous release {previous_version['release_tag']}.",
        )
        steps.append(install_step)
        if install_step.status == "FAIL":
            return _report(root, from_ref, to_ref, install_dir, previous_version, current_version, steps)

        steps.append(_verify_target_step("verify_previous_target", active, previous_launcher))
        if steps[-1].status == "FAIL":
            return _report(root, from_ref, to_ref, install_dir, previous_version, current_version, steps)
        version_step, _ = _verify_version_step(
            "verify_previous_version",
            active,
            previous_version,
            previous_root,
        )
        steps.append(version_step)
        if version_step.status == "FAIL":
            return _report(root, from_ref, to_ref, install_dir, previous_version, current_version, steps)

        update_step = _manager_step(
            "update_current",
            current_manager,
            "update",
            current_launcher,
            install_dir,
            state_file,
            current_root,
            f"Updated to current release {current_version['release_tag']}.",
        )
        steps.append(update_step)
        if update_step.status == "FAIL":
            return _report(root, from_ref, to_ref, install_dir, previous_version, current_version, steps)

        steps.append(_verify_target_step("verify_current_target", active, current_launcher))
        if steps[-1].status == "FAIL":
            return _report(root, from_ref, to_ref, install_dir, previous_version, current_version, steps)
        version_step, _ = _verify_version_step(
            "verify_current_version",
            active,
            current_version,
            current_root,
        )
        steps.append(version_step)
        if version_step.status == "FAIL":
            return _report(root, from_ref, to_ref, install_dir, previous_version, current_version, steps)

        rollback_step = _rollback_step(
            current_manager,
            install_dir,
            state_file,
            current_root,
            f"Rolled back to previous release {previous_version['release_tag']}.",
        )
        steps.append(rollback_step)
        if rollback_step.status == "FAIL":
            return _report(root, from_ref, to_ref, install_dir, previous_version, current_version, steps)

        steps.append(_verify_target_step("verify_rollback_target", active, previous_launcher))
        if steps[-1].status == "FAIL":
            return _report(root, from_ref, to_ref, install_dir, previous_version, current_version, steps)
        version_step, _ = _verify_version_step(
            "verify_rollback_version",
            active,
            previous_version,
            previous_root,
        )
        steps.append(version_step)

        return _report(root, from_ref, to_ref, install_dir, previous_version, current_version, steps)


def render_release_upgrade_smoke_summary(report: ReleaseUpgradeSmokeReport) -> str:
    status = "ok" if report.ok else "issues"
    return (
        f"AOS release-upgrade-smoke {status}: "
        f"{len(report.passed)} passed, "
        f"{len(report.failed)} failed "
        f"({report.from_ref} -> {report.to_ref})\n"
    )


def render_release_upgrade_smoke_json(report: ReleaseUpgradeSmokeReport) -> str:
    payload = {
        "ok": report.ok,
        "repo_root": str(report.repo_root),
        "from_ref": report.from_ref,
        "to_ref": report.to_ref,
        "install_dir": str(report.install_dir),
        "passed_count": len(report.passed),
        "failed_count": len(report.failed),
        "previous_version": report.previous_version,
        "current_version": report.current_version,
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


def _report(
    repo_root: Path,
    from_ref: str,
    to_ref: str,
    install_dir: Path,
    previous_version: dict[str, str],
    current_version: dict[str, str],
    steps: list[ReleaseUpgradeSmokeStep],
) -> ReleaseUpgradeSmokeReport:
    return ReleaseUpgradeSmokeReport(
        repo_root=repo_root,
        from_ref=from_ref,
        to_ref=to_ref,
        install_dir=install_dir,
        previous_version=previous_version,
        current_version=current_version,
        steps=steps,
    )


def _checkout_ref(source: Path, target: Path, ref: str, step_id: str) -> ReleaseUpgradeSmokeStep:
    clone_command = ["git", "clone", "--quiet", "--no-hardlinks", str(source), str(target)]
    clone = _run_command(clone_command, source)
    if clone.returncode != 0:
        return _failed_step(step_id, clone_command, source, clone)

    checkout_command = ["git", "checkout", "--quiet", ref]
    checkout = _run_command(checkout_command, target)
    if checkout.returncode != 0:
        return _failed_step(step_id, checkout_command, target, checkout)

    return ReleaseUpgradeSmokeStep(
        id=step_id,
        status="PASS",
        message=f"Checked out {ref}.",
        command=f"{_format_command(clone_command)}; {_format_command(checkout_command)}",
        path=str(target),
        stdout_tail=_tail((clone.stdout or "") + (checkout.stdout or "")),
        stderr_tail=_tail((clone.stderr or "") + (checkout.stderr or "")),
    )


def _manager_step(
    step_id: str,
    manager: Path,
    command_name: str,
    launcher: Path,
    install_dir: Path,
    state_file: Path,
    cwd: Path,
    success_message: str,
) -> ReleaseUpgradeSmokeStep:
    command = [
        sys.executable,
        str(manager),
        command_name,
        "--launcher",
        str(launcher),
        "--install-dir",
        str(install_dir),
        "--state-file",
        str(state_file),
    ]
    completed = _run_command(command, cwd)
    if completed.returncode != 0:
        return _failed_step(step_id, command, cwd, completed)
    return _passed_command_step(step_id, command, cwd, completed, success_message)


def _rollback_step(
    manager: Path,
    install_dir: Path,
    state_file: Path,
    cwd: Path,
    success_message: str,
) -> ReleaseUpgradeSmokeStep:
    command = [
        sys.executable,
        str(manager),
        "rollback",
        "--install-dir",
        str(install_dir),
        "--state-file",
        str(state_file),
    ]
    completed = _run_command(command, cwd)
    if completed.returncode != 0:
        return _failed_step("rollback_previous", command, cwd, completed)
    return _passed_command_step("rollback_previous", command, cwd, completed, success_message)


def _verify_target_step(step_id: str, active: Path, expected_launcher: Path) -> ReleaseUpgradeSmokeStep:
    if not active.is_symlink():
        return ReleaseUpgradeSmokeStep(
            id=step_id,
            status="FAIL",
            message=f"Installed command is not a symlink: {active}",
            path=str(active),
        )
    actual = active.resolve()
    expected = expected_launcher.resolve()
    if actual != expected:
        return ReleaseUpgradeSmokeStep(
            id=step_id,
            status="FAIL",
            message=f"Installed command points to {actual}; expected {expected}.",
            path=str(active),
        )
    return ReleaseUpgradeSmokeStep(
        id=step_id,
        status="PASS",
        message=f"Installed command points to {expected}.",
        path=str(active),
    )


def _verify_version_step(
    step_id: str,
    active: Path,
    expected: dict[str, str],
    cwd: Path,
) -> tuple[ReleaseUpgradeSmokeStep, dict[str, object] | None]:
    command = [str(active), "version", "--json"]
    completed = _run_command(command, cwd)
    if completed.returncode != 0:
        return _failed_step(step_id, command, cwd, completed), None

    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        return (
            ReleaseUpgradeSmokeStep(
                id=step_id,
                status="FAIL",
                message=f"Installed command returned invalid version JSON: {error}",
                command=_format_command(command),
                path=str(cwd),
                stdout_tail=_tail(completed.stdout),
                stderr_tail=_tail(completed.stderr),
            ),
            None,
        )

    mismatches = []
    for key in ("version", "release_channel", "release_tag"):
        if payload.get(key) != expected.get(key):
            mismatches.append(f"{key}={payload.get(key)!r}; expected {expected.get(key)!r}")
    if mismatches:
        return (
            ReleaseUpgradeSmokeStep(
                id=step_id,
                status="FAIL",
                message="Installed command version mismatch: " + "; ".join(mismatches) + ".",
                command=_format_command(command),
                path=str(cwd),
                stdout_tail=_tail(completed.stdout),
                stderr_tail=_tail(completed.stderr),
            ),
            payload,
        )

    return (
        _passed_command_step(
            step_id,
            command,
            cwd,
            completed,
            f"Installed command reports {expected['release_tag']}.",
        ),
        payload,
    )


def _read_version_info(root: Path) -> dict[str, str]:
    content = (root / "src/agentic_os/version.py").read_text(encoding="utf-8")
    version = _read_python_string_assignment(content, "VERSION")
    release_channel = _read_python_string_assignment(content, "RELEASE_CHANNEL")
    release_tag = f"v{version}-{release_channel}" if release_channel else f"v{version}"
    return {
        "version": version,
        "release_channel": release_channel,
        "release_tag": release_tag,
    }


def _read_python_string_assignment(content: str, name: str) -> str:
    pattern = rf"(?m)^{re.escape(name)}\s*=\s*[\"']([^\"']*)[\"']\s*$"
    match = re.search(pattern, content)
    if not match:
        raise ValueError(f"Missing {name} in src/agentic_os/version.py")
    return match.group(1)


def _run_command(command: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(part) for part in command],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )


def _passed_command_step(
    step_id: str,
    command: Sequence[str],
    cwd: Path,
    completed: subprocess.CompletedProcess[str],
    success_message: str,
) -> ReleaseUpgradeSmokeStep:
    return ReleaseUpgradeSmokeStep(
        id=step_id,
        status="PASS",
        message=success_message,
        command=_format_command(command),
        path=str(cwd),
        stdout_tail=_tail(completed.stdout),
        stderr_tail=_tail(completed.stderr),
    )


def _failed_step(
    step_id: str,
    command: Sequence[str],
    cwd: Path,
    completed: subprocess.CompletedProcess[str],
) -> ReleaseUpgradeSmokeStep:
    return ReleaseUpgradeSmokeStep(
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
