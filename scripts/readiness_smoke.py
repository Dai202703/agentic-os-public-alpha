#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Sequence


PROVIDERS = ["codex", "claude", "gemini", "chatgpt"]
PROVIDER_OUTPUTS = {
    "codex": "AGENTS.md",
    "claude": "CLAUDE.md",
    "gemini": "GEMINI.md",
    "chatgpt": ".agentic-os/chatgpt-project-instructions.md",
}


class SmokeFailure(RuntimeError):
    pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run an Agentic OS global readiness smoke check.")
    parser.add_argument(
        "--launcher",
        default=str(Path(__file__).resolve().parents[1] / "bin/aos"),
        help="Path to the aos launcher. Defaults to ../bin/aos relative to this script.",
    )
    parser.add_argument("--json", action="store_true", dest="as_json", help="Emit JSON metrics.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    launcher = Path(args.launcher).expanduser().resolve()
    try:
        payload = run_smoke(launcher, Path.cwd().resolve())
    except SmokeFailure as error:
        if args.as_json:
            sys.stdout.write(json.dumps({"ok": False, "error": str(error)}, indent=2, sort_keys=True))
            sys.stdout.write("\n")
        else:
            sys.stderr.write(f"AOS readiness smoke failed: {error}\n")
        return 1

    if args.as_json:
        sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True))
        sys.stdout.write("\n")
    else:
        sys.stdout.write("AOS readiness smoke passed\n")
        sys.stdout.write(f"providers_compiled={','.join(payload['providers_compiled'])}\n")
        sys.stdout.write(f"provider_outputs_verified={payload['provider_outputs_verified']}\n")
        sys.stdout.write(f"memory_entries_recorded={payload['memory_entries_recorded']}\n")
    return 0


def run_smoke(launcher: Path, execution_cwd: Path) -> dict[str, object]:
    if not launcher.is_file():
        raise SmokeFailure(f"Launcher not found: {launcher}")

    commands_run = 0
    with tempfile.TemporaryDirectory() as os_dir, tempfile.TemporaryDirectory() as project_dir:
        os_home = Path(os_dir)
        project_root = Path(project_dir)

        def run(args: list[str]) -> subprocess.CompletedProcess[str]:
            nonlocal commands_run
            commands_run += 1
            completed = subprocess.run(
                [str(launcher), *args],
                cwd=execution_cwd,
                text=True,
                capture_output=True,
                check=False,
            )
            if completed.returncode != 0:
                raise SmokeFailure(
                    "Command failed: "
                    + " ".join([str(launcher), *args])
                    + f"\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
                )
            return completed

        run(["--os-home", str(os_home), "init"])
        run(["--os-home", str(os_home), "doctor"])
        run(["--os-home", str(os_home), "doctor", "--json"])
        run(
            [
                "--os-home",
                str(os_home),
                "link-project",
                "--project-root",
                str(project_root),
                "--id",
                "demo",
                "--name",
                "Readiness Demo",
                "--provider",
                "codex",
                "--provider",
                "claude",
                "--provider",
                "gemini",
                "--provider",
                "chatgpt",
            ]
        )
        run(["--os-home", str(os_home), "doctor", "--project-root", str(project_root)])

        compiled: list[str] = []
        for provider in PROVIDERS:
            run(["--os-home", str(os_home), "compile", provider, "--project-root", str(project_root)])
            output = project_root / PROVIDER_OUTPUTS[provider]
            if not output.is_file():
                raise SmokeFailure(f"Provider output missing for {provider}: {output}")
            compiled.append(provider)

        run(
            [
                "--os-home",
                str(os_home),
                "memory",
                "add",
                "session",
                "--project-id",
                "demo",
                "--title",
                "Readiness Session",
                "--summary",
                "Verified global readiness smoke.",
                "--tag",
                "readiness",
                "--decision",
                "Use repo-contained launcher first.",
                "--artifact",
                str(project_root / "AGENTS.md"),
            ]
        )
        run(
            [
                "--os-home",
                str(os_home),
                "memory",
                "add",
                "decision",
                "--project-id",
                "demo",
                "--title",
                "Readiness Decision",
                "--rationale",
                "Global use should be validated before live installation.",
            ]
        )
        memory_list = run(["--os-home", str(os_home), "memory", "list", "--project-id", "demo"])
        memory_search = run(["--os-home", str(os_home), "memory", "search", "Global use"])

        return {
            "ok": True,
            "execution_cwd": str(execution_cwd),
            "os_home": str(os_home),
            "project_root": str(project_root),
            "commands_run": commands_run,
            "providers_compiled": compiled,
            "provider_outputs_verified": len(compiled),
            "memory_entries_recorded": 2,
            "memory_list_rows": len([line for line in memory_list.stdout.splitlines() if line.strip()]),
            "memory_search_hits": len([line for line in memory_search.stdout.splitlines() if line.strip()]),
        }


if __name__ == "__main__":
    raise SystemExit(main())
