#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Sequence


@dataclass(frozen=True)
class SmokeStep:
    id: str
    status: str
    command: str | None = None
    message: str | None = None
    stdout_tail: str | None = None
    stderr_tail: str | None = None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Smoke test the native Windows AOS installer.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--install-dir")
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--powershell")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    report = run_smoke(args)
    if args.json:
        print(json.dumps(render_payload(report), indent=2, sort_keys=True))
    else:
        print(render_summary(report))
    return 0 if all(step.status == "PASS" for step in report) else 1


def run_smoke(args: argparse.Namespace) -> list[SmokeStep]:
    root = Path(args.repo_root).expanduser().resolve()
    installer = root / "scripts/install.ps1"
    powershell = args.powershell or find_powershell()
    if not powershell:
        return [
            SmokeStep(
                id="find_powershell",
                status="FAIL",
                message="Could not find powershell or pwsh on PATH.",
            )
        ]
    if not installer.is_file():
        return [
            SmokeStep(
                id="find_installer",
                status="FAIL",
                message=f"Missing installer: {installer}",
            )
        ]

    temp_dir: tempfile.TemporaryDirectory[str] | None = None
    if args.install_dir:
        install_dir = Path(args.install_dir).expanduser().resolve()
    else:
        temp_dir = tempfile.TemporaryDirectory()
        install_dir = Path(temp_dir.name) / "aos-bin"

    try:
        steps: list[SmokeStep] = []
        steps.append(
            run_step(
                "install",
                [
                    powershell,
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(installer),
                    "-InstallDir",
                    str(install_dir),
                    "-Python",
                    args.python,
                ],
                root,
            )
        )
        if steps[-1].status == "FAIL":
            return steps

        aos_cmd = install_dir / "aos.cmd"
        aos_ps1 = install_dir / "aos.ps1"
        state_file = install_dir / ".aos-install-state.json"
        for path, step_id in ((aos_cmd, "aos_cmd_exists"), (aos_ps1, "aos_ps1_exists"), (state_file, "state_exists")):
            steps.append(path_step(step_id, path, expected_exists=True))
            if steps[-1].status == "FAIL":
                return steps

        steps.append(
            run_step(
                "aos_cmd_version",
                ["cmd.exe", "/c", str(aos_cmd), "version", "--json"] if os.name == "nt" else [str(aos_cmd), "version", "--json"],
                root,
            )
        )
        if steps[-1].status == "FAIL":
            return steps

        steps.append(
            run_step(
                "aos_ps1_version",
                [
                    powershell,
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(aos_ps1),
                    "version",
                    "--json",
                ],
                root,
            )
        )
        if steps[-1].status == "FAIL":
            return steps

        steps.append(
            run_step(
                "rollback",
                [
                    powershell,
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(installer),
                    "-InstallDir",
                    str(install_dir),
                    "-Python",
                    args.python,
                    "-Rollback",
                ],
                root,
            )
        )
        if steps[-1].status == "FAIL":
            return steps

        for path, step_id in ((aos_cmd, "aos_cmd_removed"), (aos_ps1, "aos_ps1_removed"), (state_file, "state_removed")):
            steps.append(path_step(step_id, path, expected_exists=False))
            if steps[-1].status == "FAIL":
                return steps
        return steps
    finally:
        if temp_dir is not None:
            temp_dir.cleanup()


def find_powershell() -> str | None:
    return shutil.which("powershell") or shutil.which("pwsh")


def run_step(step_id: str, command: Sequence[str], cwd: Path) -> SmokeStep:
    completed = subprocess.run(
        [str(part) for part in command],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        return SmokeStep(
            id=step_id,
            status="FAIL",
            command=format_command(command),
            message=f"Command failed with exit code {completed.returncode}.",
            stdout_tail=tail(completed.stdout),
            stderr_tail=tail(completed.stderr),
        )
    return SmokeStep(
        id=step_id,
        status="PASS",
        command=format_command(command),
        message="Command passed.",
        stdout_tail=tail(completed.stdout),
        stderr_tail=tail(completed.stderr),
    )


def path_step(step_id: str, path: Path, *, expected_exists: bool) -> SmokeStep:
    exists = path.exists()
    if exists == expected_exists:
        return SmokeStep(
            id=step_id,
            status="PASS",
            message=f"Path state matched expectation: {path}",
        )
    expectation = "exist" if expected_exists else "be removed"
    return SmokeStep(
        id=step_id,
        status="FAIL",
        message=f"Expected {path} to {expectation}.",
    )


def render_payload(steps: list[SmokeStep]) -> dict[str, object]:
    failed = [step for step in steps if step.status == "FAIL"]
    return {
        "ok": not failed,
        "passed_count": len([step for step in steps if step.status == "PASS"]),
        "failed_count": len(failed),
        "steps": [step.__dict__ for step in steps],
    }


def render_summary(steps: list[SmokeStep]) -> str:
    payload = render_payload(steps)
    status = "ok" if payload["ok"] else "issues"
    return f"AOS windows-install-smoke {status}: {payload['passed_count']} passed, {payload['failed_count']} failed"


def format_command(command: Sequence[str]) -> str:
    return " ".join(str(part) for part in command)


def tail(value: str | None, limit: int = 1200) -> str | None:
    if not value:
        return None
    return value[-limit:]


if __name__ == "__main__":
    raise SystemExit(main())
