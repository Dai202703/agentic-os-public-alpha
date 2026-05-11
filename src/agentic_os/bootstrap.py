from pathlib import Path

from .doctor import DoctorReport, doctor_os_home
from .paths import ensure_managed_directory, ensure_managed_file, resolve_os_home
from .templates import DIRECTORIES, STARTER_FILES


def init_os(os_home: str | None = None, force: bool = False) -> Path:
    root = resolve_os_home(os_home)
    root.mkdir(parents=True, exist_ok=True)

    for directory in DIRECTORIES:
        ensure_managed_directory(root, directory)

    for relative_path, content in STARTER_FILES.items():
        target = ensure_managed_file(root, relative_path)
        if force or not target.exists():
            target.write_text(content, encoding="utf-8")

    return root


def doctor_os(os_home: str | None = None) -> DoctorReport:
    return doctor_os_home(os_home)
