from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from typing import Sequence


COMMAND_TIMEOUT_SECONDS = 300
COMMAND_TIMEOUT_EXIT_CODE = 124


@dataclass(frozen=True)
class ReleaseInstallSmokeStep:
    id: str
    status: str
    message: str
    command: str | None = None
    path: str | None = None
    stdout_tail: str | None = None
    stderr_tail: str | None = None
    next_action: str | None = None


@dataclass(frozen=True)
class ReleaseInstallSmokeReport:
    source: str
    ref: str
    normalized_ref: str
    expected_tag: str | None
    clone_root: Path
    install_dir: Path
    expected_version: dict[str, str]
    installed_version: dict[str, str]
    steps: list[ReleaseInstallSmokeStep]

    @property
    def checkout_root(self) -> Path:
        return self.clone_root

    @property
    def ok(self) -> bool:
        return all(step.status == "PASS" for step in self.steps)

    @property
    def passed(self) -> list[ReleaseInstallSmokeStep]:
        return [step for step in self.steps if step.status == "PASS"]

    @property
    def failed(self) -> list[ReleaseInstallSmokeStep]:
        return [step for step in self.steps if step.status == "FAIL"]


def release_install_smoke(
    *,
    source: str | Path,
    ref: str,
    expected_tag: str | None = None,
) -> ReleaseInstallSmokeReport:
    source_value = _normalize_source(source)
    normalized_ref = normalize_release_ref(ref)
    requested_tag = release_tag_from_ref(normalized_ref)
    resolved_expected_tag = expected_tag or requested_tag
    steps: list[ReleaseInstallSmokeStep] = []
    expected_version: dict[str, str] = {}
    installed_version: dict[str, str] = {}

    with tempfile.TemporaryDirectory(prefix="aos-release-install-") as temp_dir:
        workspace = Path(temp_dir)
        clone_root = workspace / "clone"
        install_dir = workspace / "install/bin"
        check_home = workspace / "install-check-home"
        os_home = workspace / "os-home"
        active = install_dir / "aos"

        fetch_step = _fetch_ref(source_value, normalized_ref, clone_root)
        steps.append(fetch_step)
        if fetch_step.status == "FAIL":
            return _report(
                source_value,
                ref,
                normalized_ref,
                resolved_expected_tag,
                clone_root,
                install_dir,
                expected_version,
                installed_version,
                steps,
            )

        checkout_step = _checkout_ref(clone_root)
        steps.append(checkout_step)
        if checkout_step.status == "FAIL":
            return _report(
                source_value,
                ref,
                normalized_ref,
                resolved_expected_tag,
                clone_root,
                install_dir,
                expected_version,
                installed_version,
                steps,
            )

        try:
            expected_version = _read_version_info(clone_root)
        except (OSError, ValueError) as error:
            steps.append(
                ReleaseInstallSmokeStep(
                    id="read_expected_version",
                    status="FAIL",
                    message=f"Could not read release version metadata: {error}",
                    path=str(clone_root / "src/agentic_os/version.py"),
                    next_action="Ensure the release source includes src/agentic_os/version.py with VERSION and RELEASE_CHANNEL.",
                )
            )
            return _report(
                source_value,
                ref,
                normalized_ref,
                resolved_expected_tag,
                clone_root,
                install_dir,
                expected_version,
                installed_version,
                steps,
            )

        steps.append(
            ReleaseInstallSmokeStep(
                id="read_expected_version",
                status="PASS",
                message=f"Read release version metadata: {expected_version['release_tag']}.",
                path=str(clone_root / "src/agentic_os/version.py"),
            )
        )

        steps.append(_verify_ref_matches_version(expected_version, resolved_expected_tag, normalized_ref))
        if steps[-1].status == "FAIL":
            return _report(
                source_value,
                ref,
                normalized_ref,
                resolved_expected_tag,
                clone_root,
                install_dir,
                expected_version,
                installed_version,
                steps,
            )

        install_step = _install_step(clone_root, install_dir, check_home, os_home)
        steps.append(install_step)
        if install_step.status == "FAIL":
            return _report(
                source_value,
                ref,
                normalized_ref,
                resolved_expected_tag,
                clone_root,
                install_dir,
                expected_version,
                installed_version,
                steps,
            )

        steps.append(_verify_target_step(active, clone_root / "bin/aos"))
        if steps[-1].status == "FAIL":
            return _report(
                source_value,
                ref,
                normalized_ref,
                resolved_expected_tag,
                clone_root,
                install_dir,
                expected_version,
                installed_version,
                steps,
            )

        version_step, installed_version = _verify_version_step(active, expected_version, clone_root, os_home)
        steps.append(version_step)

        return _report(
            source_value,
            ref,
            normalized_ref,
            resolved_expected_tag,
            clone_root,
            install_dir,
            expected_version,
            installed_version,
            steps,
        )


def normalize_release_ref(ref: str) -> str:
    if ref.startswith("refs/"):
        return ref
    return f"refs/tags/{ref}"


def release_tag_from_ref(ref: str) -> str:
    if ref.startswith("refs/tags/"):
        return ref.removeprefix("refs/tags/")
    return ref.rsplit("/", maxsplit=1)[-1]


def render_release_install_smoke_summary(report: ReleaseInstallSmokeReport) -> str:
    status = "ok" if report.ok else "issues"
    summary = (
        f"AOS release-install-smoke {status}: "
        f"{len(report.passed)} passed, "
        f"{len(report.failed)} failed "
        f"({report.ref})\n"
    )
    if report.failed:
        first_failure = report.failed[0]
        summary += f"first_failure={first_failure.id}: {first_failure.message}\n"
        if first_failure.next_action:
            summary += f"next_action={first_failure.next_action}\n"
    return summary


def render_release_install_smoke_json(report: ReleaseInstallSmokeReport) -> str:
    payload = {
        "ok": report.ok,
        "source": report.source,
        "ref": report.ref,
        "normalized_ref": report.normalized_ref,
        "expected_tag": report.expected_tag,
        "clone_root": str(report.clone_root),
        "install_dir": str(report.install_dir),
        "passed_count": len(report.passed),
        "failed_count": len(report.failed),
        "expected_version": report.expected_version,
        "installed_version": report.installed_version,
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
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _report(
    source: str,
    ref: str,
    normalized_ref: str,
    expected_tag: str | None,
    clone_root: Path,
    install_dir: Path,
    expected_version: dict[str, str],
    installed_version: dict[str, str],
    steps: list[ReleaseInstallSmokeStep],
) -> ReleaseInstallSmokeReport:
    return ReleaseInstallSmokeReport(
        source=source,
        ref=ref,
        normalized_ref=normalized_ref,
        expected_tag=expected_tag,
        clone_root=clone_root,
        install_dir=install_dir,
        expected_version=expected_version,
        installed_version=installed_version,
        steps=steps,
    )


def _normalize_source(source: str | Path) -> str:
    source_text = str(source)
    if _looks_like_local_path(source_text):
        return str(Path(source_text).expanduser().resolve())
    return source_text


def _looks_like_local_path(value: str) -> bool:
    if "://" in value or value.startswith("git@"):
        return False
    return Path(value).expanduser().exists()


def _fetch_ref(source: str, normalized_ref: str, clone_root: Path) -> ReleaseInstallSmokeStep:
    init_command = ["git", "init", str(clone_root)]
    init = _run_command(init_command, Path.cwd())
    if init.returncode != 0:
        return _failed_step(
            "fetch_ref",
            init_command,
            Path.cwd(),
            init,
            "Ensure git can create a temporary checkout directory, then retry release-install-smoke.",
        )

    remote_command = ["git", "remote", "add", "origin", source]
    remote = _run_command(remote_command, clone_root)
    if remote.returncode != 0:
        return _failed_step(
            "fetch_ref",
            remote_command,
            clone_root,
            remote,
            "Check that the release source is a valid git remote or local repository path.",
        )

    fetch_command = ["git", "fetch", "--depth", "1", "origin", normalized_ref]
    fetch = _run_command(fetch_command, clone_root)
    if fetch.returncode != 0:
        return _failed_step(
            "fetch_ref",
            fetch_command,
            clone_root,
            fetch,
            "Check that the release source and tag exist, then retry release-install-smoke.",
        )

    return _passed_command_step(
        "fetch_ref",
        fetch_command,
        clone_root,
        fetch,
        f"Fetched {normalized_ref}.",
    )


def _checkout_ref(clone_root: Path) -> ReleaseInstallSmokeStep:
    command = ["git", "checkout", "--detach", "FETCH_HEAD"]
    completed = _run_command(command, clone_root)
    if completed.returncode != 0:
        return _failed_step(
            "checkout_ref",
            command,
            clone_root,
            completed,
            "Inspect the fetched ref and verify it resolves to a checkoutable commit.",
        )
    return _passed_command_step("checkout_ref", command, clone_root, completed, "Checked out fetched release ref.")


def _verify_ref_matches_version(
    expected_version: dict[str, str],
    expected_tag: str | None,
    normalized_ref: str,
) -> ReleaseInstallSmokeStep:
    metadata_tag = expected_version["release_tag"]
    if metadata_tag != expected_tag:
        return ReleaseInstallSmokeStep(
            id="verify_ref_matches_version",
            status="FAIL",
            message=f"Release metadata reports {metadata_tag}; expected {expected_tag} from {normalized_ref}.",
            path="src/agentic_os/version.py",
            next_action="Retag the release or update VERSION/RELEASE_CHANNEL so the tag and metadata agree.",
        )
    return ReleaseInstallSmokeStep(
        id="verify_ref_matches_version",
        status="PASS",
        message=f"Release ref matches version metadata: {metadata_tag}.",
        path="src/agentic_os/version.py",
    )


def _install_step(
    clone_root: Path,
    install_dir: Path,
    check_home: Path,
    os_home: Path,
) -> ReleaseInstallSmokeStep:
    command = ["sh", str(clone_root / "scripts/install.sh")]
    env = {
        "AOS_INSTALL_DIR": str(install_dir),
        "AOS_INSTALL_CHECK_HOME": str(check_home),
        "AOS_INSTALL_LAUNCHER": str(clone_root / "bin/aos"),
        "AOS_INSTALL_SKIP_CHECKS": "0",
        "AGENTIC_OS_HOME": str(os_home),
        "PYTHON": sys.executable,
    }
    completed = _run_command(command, clone_root, extra_env=env)
    if completed.returncode != 0:
        return _failed_step(
            "install_release",
            command,
            clone_root,
            completed,
            "Inspect install.sh output; the public release must install and pass its bundled checks.",
        )
    return _passed_command_step("install_release", command, clone_root, completed, "Install script completed.")


def _verify_target_step(active: Path, expected_launcher: Path) -> ReleaseInstallSmokeStep:
    if not active.is_symlink():
        return ReleaseInstallSmokeStep(
            id="verify_install_target",
            status="FAIL",
            message=f"Installed command is not a symlink: {active}",
            path=str(active),
            next_action="Inspect scripts/manage_global_aos.py install output and verify AOS_INSTALL_DIR was honored.",
        )
    actual = active.resolve()
    expected = expected_launcher.resolve()
    if actual != expected:
        return ReleaseInstallSmokeStep(
            id="verify_install_target",
            status="FAIL",
            message=f"Installed command points to {actual}; expected {expected}.",
            path=str(active),
            next_action="Ensure the release installer links the cloned release launcher, not another local aos command.",
        )
    return ReleaseInstallSmokeStep(
        id="verify_install_target",
        status="PASS",
        message=f"Installed command points to {expected}.",
        path=str(active),
    )


def _verify_version_step(
    active: Path,
    expected: dict[str, str],
    cwd: Path,
    os_home: Path,
) -> tuple[ReleaseInstallSmokeStep, dict[str, str]]:
    command = [str(active), "version", "--json"]
    completed = _run_command(command, cwd, extra_env={"AGENTIC_OS_HOME": str(os_home)})
    if completed.returncode != 0:
        return (
            _failed_step(
                "verify_installed_version",
                command,
                cwd,
                completed,
                "Run the installed aos version command directly and inspect launcher errors.",
            ),
            {},
        )
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        return (
            ReleaseInstallSmokeStep(
                id="verify_installed_version",
                status="FAIL",
                message=f"Installed command returned invalid version JSON: {error}",
                command=_format_command(command),
                path=str(cwd),
                stdout_tail=_tail(completed.stdout),
                stderr_tail=_tail(completed.stderr),
                next_action="Fix aos version --json so release traceability can be machine-verified.",
            ),
            {},
        )

    installed = {key: str(payload.get(key, "")) for key in ("version", "release_channel", "release_tag")}
    mismatches = []
    for key in ("version", "release_channel", "release_tag"):
        if installed.get(key) != expected.get(key):
            mismatches.append(f"{key}={installed.get(key)!r}; expected {expected.get(key)!r}")
    if mismatches:
        return (
            ReleaseInstallSmokeStep(
                id="verify_installed_version",
                status="FAIL",
                message="Installed command version mismatch: " + "; ".join(mismatches) + ".",
                command=_format_command(command),
                path=str(cwd),
                stdout_tail=_tail(completed.stdout),
                stderr_tail=_tail(completed.stderr),
                next_action="Ensure bin/aos loads the cloned release code and reports the same version metadata.",
            ),
            installed,
        )
    return (
        _passed_command_step(
            "verify_installed_version",
            command,
            cwd,
            completed,
            f"Installed command reports {expected['release_tag']}.",
        ),
        installed,
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


def _run_command(
    command: Sequence[str],
    cwd: Path,
    *,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = None
    if extra_env is not None or _is_git_command(command):
        env = _base_subprocess_env(command)
    if extra_env is not None:
        env.update(extra_env)
    command_parts = [str(part) for part in command]
    try:
        return subprocess.run(
            command_parts,
            cwd=cwd,
            env=env,
            text=True,
            capture_output=True,
            check=False,
            timeout=COMMAND_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as error:
        stderr = _timeout_output_to_text(error.stderr)
        timeout_message = f"Command timed out after {error.timeout} seconds."
        if stderr:
            timeout_message = timeout_message + "\n" + stderr
        return subprocess.CompletedProcess(
            command_parts,
            COMMAND_TIMEOUT_EXIT_CODE,
            stdout=_timeout_output_to_text(error.stdout),
            stderr=timeout_message,
        )


def _base_subprocess_env(command: Sequence[str]) -> dict[str, str]:
    env = os.environ.copy()
    for key in list(env):
        if key.startswith("AOS_INSTALL_"):
            env.pop(key)
    if _is_git_command(command):
        env["GIT_TERMINAL_PROMPT"] = "0"
    return env


def _is_git_command(command: Sequence[str]) -> bool:
    return bool(command) and Path(str(command[0])).name == "git"


def _passed_command_step(
    step_id: str,
    command: Sequence[str],
    cwd: Path,
    completed: subprocess.CompletedProcess[str],
    success_message: str,
) -> ReleaseInstallSmokeStep:
    return ReleaseInstallSmokeStep(
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
    next_action: str,
) -> ReleaseInstallSmokeStep:
    message = f"Command failed with exit code {completed.returncode}."
    if completed.returncode == COMMAND_TIMEOUT_EXIT_CODE and completed.stderr:
        message = completed.stderr.splitlines()[0]
    return ReleaseInstallSmokeStep(
        id=step_id,
        status="FAIL",
        message=message,
        command=_format_command(command),
        path=str(cwd),
        stdout_tail=_tail(completed.stdout),
        stderr_tail=_tail(completed.stderr),
        next_action=next_action,
    )


def _format_command(command: Sequence[str]) -> str:
    return " ".join(str(part) for part in command)


def _tail(value: str | None, limit: int = 1200) -> str | None:
    if not value:
        return None
    return value[-limit:]


def _timeout_output_to_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value
