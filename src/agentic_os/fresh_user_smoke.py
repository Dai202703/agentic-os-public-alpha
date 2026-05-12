from dataclasses import dataclass
import json
import os
from pathlib import Path
import subprocess
import tempfile
from typing import Sequence


PROVIDERS = ["codex", "claude", "gemini", "chatgpt"]
PROVIDER_OUTPUTS = {
    "codex": "AGENTS.md",
    "claude": "CLAUDE.md",
    "gemini": "GEMINI.md",
    "chatgpt": ".agentic-os/chatgpt-project-instructions.md",
}


@dataclass(frozen=True)
class FreshUserSmokeStep:
    id: str
    status: str
    message: str
    command: str | None = None
    path: str | None = None
    stdout_tail: str | None = None
    stderr_tail: str | None = None


@dataclass(frozen=True)
class FreshUserSmokeReport:
    repo_root: Path
    install_dir: Path
    os_home: Path
    project_root: Path
    project_id: str
    steps: list[FreshUserSmokeStep]

    @property
    def ok(self) -> bool:
        return all(step.status == "PASS" for step in self.steps)

    @property
    def passed(self) -> list[FreshUserSmokeStep]:
        return [step for step in self.steps if step.status == "PASS"]

    @property
    def failed(self) -> list[FreshUserSmokeStep]:
        return [step for step in self.steps if step.status == "FAIL"]


def fresh_user_smoke(
    repo_root: str | Path = ".",
    launcher: str | Path | None = None,
) -> FreshUserSmokeReport:
    root = Path(repo_root).expanduser().resolve()
    launcher_path = Path(launcher).expanduser().resolve() if launcher else root / "bin/aos"
    project_id = "fresh-user-demo"
    steps: list[FreshUserSmokeStep] = []

    with tempfile.TemporaryDirectory(prefix="aos-fresh-user-") as temp_dir:
        workspace = Path(temp_dir)
        install_dir = workspace / "bin"
        os_home = workspace / "os-home"
        project_root = workspace / "demo-project"
        active = install_dir / "aos"
        env = _build_env(install_dir, os_home)

        install_step = _install_step(root, launcher_path, install_dir, workspace, env)
        steps.append(install_step)
        if install_step.status == "FAIL":
            return _report(root, install_dir, os_home, project_root, project_id, steps)

        version_step = _run_command_step(
            "installed_version",
            [active, "version", "--json"],
            root,
            env,
            "Installed command returned version metadata.",
        )
        steps.append(version_step)
        if version_step.status == "FAIL":
            return _report(root, install_dir, os_home, project_root, project_id, steps)

        for step_id, command, message in (
            (
                "init_os_home",
                [active, "--os-home", os_home, "init"],
                "Temporary OS home initialized.",
            ),
            (
                "doctor_os_home",
                [active, "--os-home", os_home, "doctor", "--summary"],
                "Temporary OS home doctor passed.",
            ),
        ):
            step = _run_command_step(step_id, command, root, env, message)
            steps.append(step)
            if step.status == "FAIL":
                return _report(root, install_dir, os_home, project_root, project_id, steps)

        steps.append(_create_demo_project_step(project_root))
        if steps[-1].status == "FAIL":
            return _report(root, install_dir, os_home, project_root, project_id, steps)

        link_step = _run_command_step(
            "link_project",
            [
                active,
                "--os-home",
                os_home,
                "link-project",
                "--project-root",
                project_root,
                "--id",
                project_id,
                "--name",
                "Fresh User Demo",
                "--provider",
                "codex",
                "--provider",
                "claude",
                "--provider",
                "gemini",
                "--provider",
                "chatgpt",
            ],
            root,
            env,
            "Demo project linked with all supported providers.",
        )
        steps.append(link_step)
        if link_step.status == "FAIL":
            return _report(root, install_dir, os_home, project_root, project_id, steps)

        for provider in PROVIDERS:
            compile_step = _compile_provider_step(active, os_home, project_root, provider, root, env)
            steps.append(compile_step)
            if compile_step.status == "FAIL":
                return _report(root, install_dir, os_home, project_root, project_id, steps)

        onboarding_step = _onboarding_step(active, os_home, project_root, root, env)
        steps.append(onboarding_step)
        return _report(root, install_dir, os_home, project_root, project_id, steps)


def render_fresh_user_smoke_summary(report: FreshUserSmokeReport) -> str:
    status = "ok" if report.ok else "issues"
    return (
        f"AOS fresh-user-smoke {status}: "
        f"{len(report.passed)} passed, "
        f"{len(report.failed)} failed "
        f"({report.project_id})\n"
    )


def render_fresh_user_smoke_json(report: FreshUserSmokeReport) -> str:
    payload = {
        "ok": report.ok,
        "repo_root": str(report.repo_root),
        "install_dir": str(report.install_dir),
        "os_home": str(report.os_home),
        "project_root": str(report.project_root),
        "project_id": report.project_id,
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


def _report(
    repo_root: Path,
    install_dir: Path,
    os_home: Path,
    project_root: Path,
    project_id: str,
    steps: list[FreshUserSmokeStep],
) -> FreshUserSmokeReport:
    return FreshUserSmokeReport(
        repo_root=repo_root,
        install_dir=install_dir,
        os_home=os_home,
        project_root=project_root,
        project_id=project_id,
        steps=steps,
    )


def _build_env(install_dir: Path, os_home: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["AGENTIC_OS_HOME"] = str(os_home)
    env["PATH"] = f"{install_dir}{os.pathsep}{env.get('PATH', '')}"
    return env


def _install_step(
    root: Path,
    launcher: Path,
    install_dir: Path,
    workspace: Path,
    env: dict[str, str],
) -> FreshUserSmokeStep:
    script = root / "scripts/install.sh"
    command = ["sh", str(script)]
    install_env = env.copy()
    install_env["AOS_INSTALL_DIR"] = str(install_dir)
    install_env["AOS_INSTALL_LAUNCHER"] = str(launcher)
    install_env["AOS_INSTALL_CHECK_HOME"] = str(workspace / "install-check-home")
    completed = _run_command(command, root, install_env)
    if completed.returncode != 0:
        return _failed_step("install_wrapper", command, root, completed)
    active = install_dir / "aos"
    if not active.is_file():
        return FreshUserSmokeStep(
            id="install_wrapper",
            status="FAIL",
            message=f"Install wrapper completed but installed command is missing: {active}",
            command=_format_command(command),
            path=str(install_dir),
            stdout_tail=_tail(completed.stdout),
            stderr_tail=_tail(completed.stderr),
        )
    return _passed_command_step(
        "install_wrapper",
        command,
        root,
        completed,
        f"Install wrapper created isolated command at {active}.",
    )


def _create_demo_project_step(project_root: Path) -> FreshUserSmokeStep:
    try:
        project_root.mkdir(parents=True, exist_ok=True)
        (project_root / "README.md").write_text("# Fresh User Demo\n", encoding="utf-8")
    except OSError as error:
        return FreshUserSmokeStep(
            id="create_demo_project",
            status="FAIL",
            message=f"Could not create demo project: {error}",
            path=str(project_root),
        )
    return FreshUserSmokeStep(
        id="create_demo_project",
        status="PASS",
        message="Temporary demo project created.",
        path=str(project_root),
    )


def _compile_provider_step(
    active: Path,
    os_home: Path,
    project_root: Path,
    provider: str,
    cwd: Path,
    env: dict[str, str],
) -> FreshUserSmokeStep:
    command = [active, "--os-home", os_home, "compile", provider, "--project-root", project_root]
    completed = _run_command(command, cwd, env)
    if completed.returncode != 0:
        return _failed_step(f"compile_{provider}", command, cwd, completed)

    output = project_root / PROVIDER_OUTPUTS[provider]
    if not output.is_file():
        return FreshUserSmokeStep(
            id=f"compile_{provider}",
            status="FAIL",
            message=f"Provider output missing for {provider}: {output}",
            command=_format_command(command),
            path=str(output),
            stdout_tail=_tail(completed.stdout),
            stderr_tail=_tail(completed.stderr),
        )

    return _passed_command_step(
        f"compile_{provider}",
        command,
        cwd,
        completed,
        f"Compiled {provider} provider output.",
        path=output,
    )


def _onboarding_step(
    active: Path,
    os_home: Path,
    project_root: Path,
    cwd: Path,
    env: dict[str, str],
) -> FreshUserSmokeStep:
    command = [
        active,
        "--os-home",
        os_home,
        "onboarding-check",
        "--project-root",
        project_root,
        "--json",
    ]
    completed = _run_command(command, cwd, env)
    if completed.returncode != 0:
        return _failed_step("fresh_user_onboarding", command, cwd, completed)
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        return FreshUserSmokeStep(
            id="fresh_user_onboarding",
            status="FAIL",
            message=f"Onboarding check did not emit valid JSON: {error}",
            command=_format_command(command),
            path=str(project_root),
            stdout_tail=_tail(completed.stdout),
            stderr_tail=_tail(completed.stderr),
        )
    if payload.get("ok") is not True:
        return FreshUserSmokeStep(
            id="fresh_user_onboarding",
            status="FAIL",
            message="Onboarding check returned ok=false.",
            command=_format_command(command),
            path=str(project_root),
            stdout_tail=_tail(completed.stdout),
            stderr_tail=_tail(completed.stderr),
        )
    return _passed_command_step(
        "fresh_user_onboarding",
        command,
        cwd,
        completed,
        "Fresh user project onboarding passed.",
        path=project_root,
    )


def _run_command_step(
    step_id: str,
    command: Sequence[object],
    cwd: Path,
    env: dict[str, str],
    success_message: str,
) -> FreshUserSmokeStep:
    completed = _run_command(command, cwd, env)
    if completed.returncode != 0:
        return _failed_step(step_id, command, cwd, completed)
    return _passed_command_step(step_id, command, cwd, completed, success_message)


def _run_command(
    command: Sequence[object],
    cwd: Path,
    env: dict[str, str],
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(part) for part in command],
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def _passed_command_step(
    step_id: str,
    command: Sequence[object],
    cwd: Path,
    completed: subprocess.CompletedProcess[str],
    message: str,
    *,
    path: Path | None = None,
) -> FreshUserSmokeStep:
    return FreshUserSmokeStep(
        id=step_id,
        status="PASS",
        message=message,
        command=_format_command(command),
        path=str(path or cwd),
        stdout_tail=_tail(completed.stdout),
        stderr_tail=_tail(completed.stderr),
    )


def _failed_step(
    step_id: str,
    command: Sequence[object],
    cwd: Path,
    completed: subprocess.CompletedProcess[str],
) -> FreshUserSmokeStep:
    return FreshUserSmokeStep(
        id=step_id,
        status="FAIL",
        message=f"Command failed with exit code {completed.returncode}.",
        command=_format_command(command),
        path=str(cwd),
        stdout_tail=_tail(completed.stdout),
        stderr_tail=_tail(completed.stderr),
    )


def _format_command(command: Sequence[object]) -> str:
    return " ".join(str(part) for part in command)


def _tail(value: str | None, limit: int = 1200) -> str | None:
    if not value:
        return None
    return value[-limit:]
