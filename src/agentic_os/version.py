from dataclasses import asdict, dataclass
import json
import os
import platform
from pathlib import Path
import shutil
import sys

from .paths import resolve_os_home


VERSION = "0.1.14"
RELEASE_CHANNEL = "public-alpha"


@dataclass(frozen=True)
class VersionInfo:
    version: str
    release_channel: str
    release_tag: str
    python_version: str
    python_executable: str
    command_path: str
    os_home: str


def get_release_tag(version: str = VERSION, release_channel: str = RELEASE_CHANNEL) -> str:
    if release_channel:
        return f"v{version}-{release_channel}"
    return f"v{version}"


def collect_version_info(os_home: str | Path | None = None) -> VersionInfo:
    command_path = os.environ.get("AOS_COMMAND_PATH") or shutil.which("aos") or sys.argv[0]
    return VersionInfo(
        version=VERSION,
        release_channel=RELEASE_CHANNEL,
        release_tag=get_release_tag(),
        python_version=platform.python_version(),
        python_executable=str(Path(sys.executable).expanduser().resolve()),
        command_path=str(Path(command_path).expanduser().resolve()),
        os_home=str(resolve_os_home(os_home)),
    )


def render_version_text(info: VersionInfo) -> str:
    return (
        f"AOS version {info.version}\n"
        f"Release channel: {info.release_channel}\n"
        f"Release tag: {info.release_tag}\n"
        f"Python version: {info.python_version}\n"
        f"Python executable: {info.python_executable}\n"
        f"Command path: {info.command_path}\n"
        f"OS home: {info.os_home}\n"
    )


def render_version_json(info: VersionInfo) -> str:
    return json.dumps(asdict(info), indent=2, sort_keys=True) + "\n"
