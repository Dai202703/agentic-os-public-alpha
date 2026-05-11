from dataclasses import dataclass
import json
from pathlib import Path

from .doctor import DoctorReport, doctor_project
from .memory_index import list_memory
from .paths import ensure_readable_file, resolve_os_home, resolve_project_root
from .project import read_project_config, validate_project_config


@dataclass(frozen=True)
class ReadinessReport:
    doctor_report: DoctorReport
    project_id: str
    provider_count: int
    memory_ok: bool

    @property
    def ok(self) -> bool:
        return (
            not self.doctor_report.errors
            and not self.doctor_report.warnings
            and self.memory_ok
        )


def readiness_project(os_home: str | Path | None, project_root: str | Path) -> ReadinessReport:
    root = resolve_os_home(os_home)
    resolved_project_root = resolve_project_root(project_root)
    doctor_report = doctor_project(root, resolved_project_root)
    project_id, provider_count = _read_project_readiness_metadata(resolved_project_root)
    return ReadinessReport(
        doctor_report=doctor_report,
        project_id=project_id,
        provider_count=provider_count,
        memory_ok=_memory_is_readable(root, project_id),
    )


def render_readiness_summary(report: ReadinessReport) -> str:
    status = "ok" if report.ok else "issues"
    memory_status = "memory ok" if report.memory_ok else "memory unavailable"
    return (
        f"AOS readiness {status}: "
        f"{len(report.doctor_report.errors)} errors, "
        f"{len(report.doctor_report.warnings)} warnings, "
        f"{report.provider_count} providers, "
        f"{memory_status}\n"
    )


def render_readiness_json(report: ReadinessReport) -> str:
    doctor_report = report.doctor_report
    payload = {
        "ok": report.ok,
        "os_home": str(doctor_report.root),
        "project_root": str(doctor_report.project_root) if doctor_report.project_root else None,
        "project_id": report.project_id,
        "providers_count": report.provider_count,
        "memory_ok": report.memory_ok,
        "errors_count": len(doctor_report.errors),
        "warnings_count": len(doctor_report.warnings),
        "issues": [
            {
                "severity": issue.severity,
                "code": issue.code,
                "message": issue.message,
                "path": issue.path,
                "suggested_action": issue.suggested_action,
                "line": issue.line,
            }
            for issue in doctor_report.issues
        ],
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _read_project_readiness_metadata(project_root: Path) -> tuple[str, int]:
    try:
        config_path = ensure_readable_file(
            project_root,
            ".agentic-os/project.yaml",
            "Project config",
        )
        config = validate_project_config(read_project_config(config_path))
    except (OSError, UnicodeDecodeError, ValueError):
        return "", 0

    providers = config.get("providers", [])
    provider_count = len(providers) if isinstance(providers, list) else 0
    return str(config.get("id", "")), provider_count


def _memory_is_readable(os_home: Path, project_id: str) -> bool:
    if not project_id:
        return False
    try:
        list_memory(os_home, project_id=project_id, limit=1)
    except (OSError, UnicodeDecodeError, ValueError):
        return False
    return True
