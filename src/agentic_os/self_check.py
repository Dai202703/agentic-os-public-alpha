from dataclasses import dataclass
import json
from pathlib import Path
import shutil

from .doctor import doctor_os_home
from .paths import resolve_os_home, resolve_project_root
from .readiness import readiness_project


@dataclass(frozen=True)
class SelfCheckItem:
    id: str
    status: str
    message: str
    path: str | None = None


@dataclass(frozen=True)
class SelfCheckReport:
    checks: list[SelfCheckItem]

    @property
    def ok(self) -> bool:
        return all(check.status == "PASS" for check in self.checks)

    @property
    def passed(self) -> list[SelfCheckItem]:
        return [check for check in self.checks if check.status == "PASS"]

    @property
    def failed(self) -> list[SelfCheckItem]:
        return [check for check in self.checks if check.status == "FAIL"]


def self_check(
    os_home: str | Path | None = None,
    project_root: str | Path = ".",
) -> SelfCheckReport:
    root = resolve_os_home(os_home)
    resolved_project_root = resolve_project_root(project_root)
    return SelfCheckReport(
        checks=[
            _command_on_path_check(),
            _os_home_check(root),
            _project_readiness_check(root, resolved_project_root),
        ]
    )


def render_self_check_summary(report: SelfCheckReport) -> str:
    status = "ok" if report.ok else "issues"
    return (
        f"AOS self-check {status}: "
        f"{len(report.passed)} passed, "
        f"{len(report.failed)} failed\n"
    )


def render_self_check_json(report: SelfCheckReport) -> str:
    payload = {
        "ok": report.ok,
        "passed_count": len(report.passed),
        "failed_count": len(report.failed),
        "checks": [
            {
                "id": check.id,
                "status": check.status,
                "message": check.message,
                "path": check.path,
            }
            for check in report.checks
        ],
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _command_on_path_check() -> SelfCheckItem:
    command_path = shutil.which("aos")
    if command_path:
        return SelfCheckItem(
            id="command_on_path",
            status="PASS",
            message="aos command is available on PATH.",
            path=command_path,
        )
    return SelfCheckItem(
        id="command_on_path",
        status="FAIL",
        message="aos command is not available on PATH.",
    )


def _os_home_check(os_home: Path) -> SelfCheckItem:
    report = doctor_os_home(os_home)
    if report.ok:
        return SelfCheckItem(
            id="os_home",
            status="PASS",
            message="Agentic OS home is ready.",
            path=str(report.root),
        )
    return SelfCheckItem(
        id="os_home",
        status="FAIL",
        message=f"Agentic OS home has {len(report.errors)} errors.",
        path=str(report.root),
    )


def _project_readiness_check(os_home: Path, project_root: Path) -> SelfCheckItem:
    report = readiness_project(os_home, project_root)
    if report.ok:
        return SelfCheckItem(
            id="project_readiness",
            status="PASS",
            message="Project readiness gate passed.",
            path=str(report.doctor_report.project_root),
        )
    return SelfCheckItem(
        id="project_readiness",
        status="FAIL",
        message=(
            f"Project readiness has {len(report.doctor_report.errors)} errors, "
            f"{len(report.doctor_report.warnings)} warnings, "
            f"memory_ok={str(report.memory_ok).lower()}."
        ),
        path=str(report.doctor_report.project_root),
    )
