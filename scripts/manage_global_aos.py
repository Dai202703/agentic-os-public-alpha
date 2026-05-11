#!/usr/bin/env python3
import argparse
from datetime import datetime
import json
from pathlib import Path
import sys


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command in {"install", "update"}:
            return activate_launcher(args)
        if args.command == "rollback":
            return rollback_launcher(args)
        if args.command == "status":
            return print_status(args)
    except (OSError, ValueError) as error:
        sys.stderr.write(f"Error: {error}\n")
        return 1

    parser.print_help(sys.stderr)
    return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Install, update, inspect, or roll back the global aos command symlink."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    for command in ("install", "update"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("--launcher", required=True)
        add_common_paths(subparser)

    rollback = subparsers.add_parser("rollback")
    add_common_paths(rollback)

    status = subparsers.add_parser("status")
    add_common_paths(status)

    return parser


def add_common_paths(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--install-dir", default=str(Path.home() / ".local/bin"))
    parser.add_argument("--state-file")


def activate_launcher(args: argparse.Namespace) -> int:
    launcher = require_regular_file(Path(args.launcher).expanduser())
    install_dir = Path(args.install_dir).expanduser()
    install_dir.mkdir(parents=True, exist_ok=True)
    active = install_dir / "aos"
    state_file = resolve_state_file(args, install_dir)
    backup_path: str | None = None

    if active.is_symlink() and active.resolve() == launcher.resolve():
        write_state(
            state_file,
            {
                "active_path": str(active),
                "backup_path": None,
                "launcher": str(launcher.resolve()),
            },
        )
        print(f"aos already points to {launcher.resolve()}")
        return 0

    if active.exists() or active.is_symlink():
        if active.is_dir() and not active.is_symlink():
            raise ValueError(f"Refusing to replace directory: {active}")
        backup = next_backup_path(install_dir)
        active.rename(backup)
        backup_path = str(backup)

    active.symlink_to(launcher.resolve())
    write_state(
        state_file,
        {
            "active_path": str(active),
            "backup_path": backup_path,
            "launcher": str(launcher.resolve()),
        },
    )
    print(f"Linked {active} -> {launcher.resolve()}")
    return 0


def rollback_launcher(args: argparse.Namespace) -> int:
    install_dir = Path(args.install_dir).expanduser()
    active = install_dir / "aos"
    state_file = resolve_state_file(args, install_dir)
    state = read_state(state_file)
    backup_value = state.get("backup_path")

    if active.exists() or active.is_symlink():
        if active.is_dir() and not active.is_symlink():
            raise ValueError(f"Refusing to remove directory during rollback: {active}")
        active.unlink()

    if backup_value:
        backup = Path(str(backup_value)).expanduser()
        if not backup.exists() and not backup.is_symlink():
            raise ValueError(f"Recorded backup is missing: {backup}")
        backup.rename(active)
        print(f"Restored {active} from {backup}")
    else:
        print(f"Removed {active}; no previous aos command was recorded")

    write_state(
        state_file,
        {
            "active_path": str(active),
            "backup_path": None,
            "launcher": None,
        },
    )
    return 0


def print_status(args: argparse.Namespace) -> int:
    install_dir = Path(args.install_dir).expanduser()
    active = install_dir / "aos"
    state_file = resolve_state_file(args, install_dir)

    payload = {
        "active_path": str(active),
        "exists": active.exists() or active.is_symlink(),
        "is_symlink": active.is_symlink(),
        "target": str(active.resolve()) if active.exists() or active.is_symlink() else None,
        "state_file": str(state_file),
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def resolve_state_file(args: argparse.Namespace, install_dir: Path) -> Path:
    if args.state_file:
        return Path(args.state_file).expanduser()
    return install_dir / ".aos-install-state.json"


def require_regular_file(path: Path) -> Path:
    resolved = path.resolve()
    if not resolved.is_file():
        raise ValueError(f"Launcher is not a regular file: {path}")
    return resolved


def next_backup_path(install_dir: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    candidate = install_dir / f"aos.backup-{timestamp}"
    suffix = 1
    while candidate.exists() or candidate.is_symlink():
        candidate = install_dir / f"aos.backup-{timestamp}-{suffix}"
        suffix += 1
    return candidate


def read_state(state_file: Path) -> dict[str, object]:
    if not state_file.is_file():
        raise ValueError(f"Install state file is missing: {state_file}")
    return json.loads(state_file.read_text(encoding="utf-8"))


def write_state(state_file: Path, payload: dict[str, object]) -> None:
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
