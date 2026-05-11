from dataclasses import dataclass
import json
from pathlib import Path

from .compiler import compile_provider
from .paths import ensure_readable_file, resolve_os_home, resolve_project_root
from .project import read_project_config, validate_project_config
from .readiness import ReadinessReport, readiness_project
from .self_check import SelfCheckReport, self_check


PRIVATE_SCAN_ISSUE_CODES = {
    "SENSITIVE_FILENAME",
    "SECRET_PATTERN",
    "LOCAL_PATH_PATTERN",
    "PRIVATE_MEMORY_REFERENCE",
}


@dataclass(frozen=True)
class OnboardingCheckStep:
    id: str
    status: str
    message: str
    path: str | None = None


@dataclass(frozen=True)
class OnboardingCheckReport:
    steps: list[OnboardingCheckStep]

    @property
    def ok(self) -> bool:
        return all(step.status == "PASS" for step in self.steps)

    @property
    def passed(self) -> list[OnboardingCheckStep]:
        return [step for step in self.steps if step.status == "PASS"]

    @property
    def failed(self) -> list[OnboardingCheckStep]:
        return [step for step in self.steps if step.status == "FAIL"]


def onboarding_check(
    os_home: str | Path | None = None,
    project_root: str | Path = ".",
) -> OnboardingCheckReport:
    root = resolve_os_home(os_home)
    resolved_project_root = resolve_project_root(project_root)

    compile_step = _compile_enabled_providers(root, resolved_project_root)
    self_check_report = self_check(root, resolved_project_root)
    readiness_report = readiness_project(root, resolved_project_root)
    return OnboardingCheckReport(
        steps=[
            compile_step,
            _self_check_step(self_check_report, resolved_project_root),
            _readiness_step(readiness_report),
            _private_scan_step(readiness_report),
        ]
    )


def render_onboarding_check_summary(report: OnboardingCheckReport) -> str:
    status = "ok" if report.ok else "issues"
    return (
        f"AOS onboarding-check {status}: "
        f"{len(report.passed)} passed, "
        f"{len(report.failed)} failed\n"
    )


def render_onboarding_check_json(report: OnboardingCheckReport) -> str:
    payload = {
        "ok": report.ok,
        "passed_count": len(report.passed),
        "failed_count": len(report.failed),
        "steps": [
            {
                "id": step.id,
                "status": step.status,
                "message": step.message,
                "path": step.path,
            }
            for step in report.steps
        ],
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _compile_enabled_providers(os_home: Path, project_root: Path) -> OnboardingCheckStep:
    try:
        providers = _read_enabled_providers(project_root)
        output_paths = [
            compile_provider(os_home, project_root, provider)
            for provider in providers
        ]
    except (OSError, UnicodeDecodeError, ValueError) as error:
        return OnboardingCheckStep(
            id="compile_providers",
            status="FAIL",
            message=f"Provider compilation failed: {error}",
            path=str(project_root),
        )

    return OnboardingCheckStep(
        id="compile_providers",
        status="PASS",
        message=f"Compiled {len(output_paths)} provider outputs.",
        path=str(project_root),
    )


def _read_enabled_providers(project_root: Path) -> list[str]:
    config_path = ensure_readable_file(
        project_root,
        ".agentic-os/project.yaml",
        "Project config",
    )
    config = validate_project_config(read_project_config(config_path))
    providers = config.get("providers", [])
    return [str(provider) for provider in providers] if isinstance(providers, list) else []


def _self_check_step(
    self_check_report: SelfCheckReport,
    project_root: Path,
) -> OnboardingCheckStep:
    failed_count = len(self_check_report.failed)
    if self_check_report.ok:
        return OnboardingCheckStep(
            id="self_check",
            status="PASS",
            message="Self-check passed.",
            path=str(project_root),
        )
    return OnboardingCheckStep(
        id="self_check",
        status="FAIL",
        message=f"Self-check has {failed_count} failed checks.",
        path=str(project_root),
    )


def _readiness_step(report: ReadinessReport) -> OnboardingCheckStep:
    project_root = report.doctor_report.project_root
    if report.ok:
        return OnboardingCheckStep(
            id="readiness",
            status="PASS",
            message="Readiness gate passed.",
            path=str(project_root),
        )
    return OnboardingCheckStep(
        id="readiness",
        status="FAIL",
        message=(
            f"Readiness has {len(report.doctor_report.errors)} errors, "
            f"{len(report.doctor_report.warnings)} warnings, "
            f"memory_ok={str(report.memory_ok).lower()}."
        ),
        path=str(project_root),
    )


def _private_scan_step(report: ReadinessReport) -> OnboardingCheckStep:
    findings = [
        issue
        for issue in report.doctor_report.issues
        if issue.code in PRIVATE_SCAN_ISSUE_CODES
    ]
    project_root = report.doctor_report.project_root
    if not findings:
        return OnboardingCheckStep(
            id="private_scan",
            status="PASS",
            message="Private scan passed.",
            path=str(project_root),
        )
    return OnboardingCheckStep(
        id="private_scan",
        status="FAIL",
        message=f"Private scan has {len(findings)} findings.",
        path=str(project_root),
    )
