from dataclasses import dataclass
import json
from pathlib import Path
import tempfile

from .compiler import (
    PROVIDER_FILES,
    extract_context_fingerprint,
    provider_context_fingerprint,
    resolve_context_path,
)
from .paths import resolve_os_home
from .paths import (
    ensure_readable_file,
    reject_symlink_components,
    resolve_project_root,
    validate_relative_path,
)
from .project import read_project_config, validate_project_config
from .security import SecurityFinding, scan_private_data
from .templates import DIRECTORIES, STARTER_FILES


@dataclass(frozen=True)
class DoctorIssue:
    severity: str
    code: str
    message: str
    path: str
    suggested_action: str
    line: int | None = None


@dataclass(frozen=True)
class DoctorReport:
    root: Path
    ok: bool
    issues: list[DoctorIssue]
    project_root: Path | None = None

    @property
    def errors(self) -> list[DoctorIssue]:
        return [issue for issue in self.issues if issue.severity == "ERROR"]

    @property
    def warnings(self) -> list[DoctorIssue]:
        return [issue for issue in self.issues if issue.severity == "WARN"]

    @property
    def missing(self) -> list[str]:
        return [
            issue.path
            for issue in self.issues
            if issue.code in {"MISSING_REQUIRED_DIRECTORY", "MISSING_REQUIRED_FILE"}
        ]


def doctor_os_home(os_home: str | Path | None = None) -> DoctorReport:
    root = resolve_os_home(os_home)
    issues: list[DoctorIssue] = []
    reported_symlinks: set[str] = set()

    for directory in DIRECTORIES:
        path = root / directory
        symlink_component = _symlink_component(root, Path(directory))
        if symlink_component:
            symlink_path = symlink_component.as_posix()
            if symlink_path not in reported_symlinks:
                reported_symlinks.add(symlink_path)
                issues.append(
                    DoctorIssue(
                        "ERROR",
                        "MANAGED_PATH_SYMLINK",
                        f"Managed directory may not be a symlink: {symlink_path}",
                        symlink_path,
                        "Replace the symlink with a real directory inside the Agentic OS home.",
                    )
                )
        elif not path.exists():
            issues.append(
                DoctorIssue(
                    "ERROR",
                    "MISSING_REQUIRED_DIRECTORY",
                    f"Required directory is missing: {directory}",
                    directory,
                    "Run aos init to create required directories.",
                )
            )
        elif not path.is_dir():
            issues.append(
                DoctorIssue(
                    "ERROR",
                    "MANAGED_PATH_NOT_DIRECTORY",
                    f"Required path is not a directory: {directory}",
                    directory,
                    "Remove the file and run aos init again.",
                )
            )

    for relative in STARTER_FILES:
        path = root / relative
        symlink_component = _symlink_component(root, Path(relative))
        if symlink_component:
            symlink_path = symlink_component.as_posix()
            if symlink_path not in reported_symlinks:
                reported_symlinks.add(symlink_path)
                issues.append(
                    DoctorIssue(
                        "ERROR",
                        "MANAGED_PATH_SYMLINK",
                        f"Managed file may not be a symlink: {symlink_path}",
                        symlink_path,
                        "Replace the symlink with a real file inside the Agentic OS home.",
                    )
                )
        elif not path.exists():
            issues.append(
                DoctorIssue(
                    "ERROR",
                    "MISSING_REQUIRED_FILE",
                    f"Required file is missing: {relative}",
                    relative,
                    "Run aos init to create starter files.",
                )
            )
        elif not path.is_file():
            issues.append(
                DoctorIssue(
                    "ERROR",
                    "MANAGED_PATH_NOT_FILE",
                    f"Required path is not a file: {relative}",
                    relative,
                    "Remove the path and run aos init again.",
                )
            )

    if root.exists() and root.is_dir() and not _can_write_directory(root):
        issues.append(
            DoctorIssue(
                "ERROR",
                "OS_HOME_NOT_WRITABLE",
                "Agentic OS home is not writable.",
                str(root),
                "Fix directory permissions so AOS can write memory, skills, workflows, and config.",
            )
        )

    return DoctorReport(
        root=root,
        ok=not any(issue.severity == "ERROR" for issue in issues),
        issues=issues,
    )


def doctor_project(os_home: str | Path | None, project_root: str | Path) -> DoctorReport:
    root = resolve_os_home(os_home)
    resolved_project_root = resolve_project_root(project_root)
    issues: list[DoctorIssue] = []

    try:
        config_path = ensure_readable_file(
            resolved_project_root,
            ".agentic-os/project.yaml",
            "Project config",
        )
    except FileNotFoundError:
        issues.append(
            DoctorIssue(
                "ERROR",
                "PROJECT_CONFIG_MISSING",
                "Project config is missing: .agentic-os/project.yaml",
                str(resolved_project_root / ".agentic-os/project.yaml"),
                "Run aos link-project for this project.",
            )
        )
        return _project_report(root, resolved_project_root, issues)
    except (OSError, ValueError) as error:
        issues.append(_invalid_project_config_issue(resolved_project_root, str(error)))
        return _project_report(root, resolved_project_root, issues)

    try:
        config = validate_project_config(read_project_config(config_path))
        contexts = config.get("contexts", [])
        if not isinstance(contexts, list):
            raise ValueError("Project config must declare a contexts list")
        for context in contexts:
            context_path = resolve_context_path(root, str(context))
            if not context_path.exists():
                raise FileNotFoundError(context_path)
        expected_context_headings = _expected_context_headings(root, contexts)
    except (OSError, UnicodeDecodeError, ValueError) as error:
        issues.append(_invalid_project_config_issue(resolved_project_root, str(error)))
        return _project_report(root, resolved_project_root, issues)

    declared_providers = [str(provider) for provider in config.get("providers", [])]
    declared_provider_set = set(declared_providers)
    existing_outputs: list[Path] = []
    for provider in declared_providers:
        template_relative, output_relative = PROVIDER_FILES[provider]
        try:
            ensure_readable_file(root, template_relative, "Provider template")
        except FileNotFoundError:
            template_path = root / template_relative
            issues.append(
                DoctorIssue(
                    "ERROR",
                    "PROVIDER_TEMPLATE_MISSING",
                    f"Provider template is missing for {provider}: {template_relative}",
                    str(template_path),
                    "Run aos init or restore the missing provider template.",
                )
            )
        except (OSError, ValueError) as error:
            issues.append(
                DoctorIssue(
                    "ERROR",
                    "PROVIDER_TEMPLATE_UNSAFE",
                    f"Provider template is unsafe for {provider}: {error}",
                    str(root / template_relative),
                    "Replace the provider template with a regular file inside the Agentic OS home.",
                )
            )

    for provider, (_, output_relative) in PROVIDER_FILES.items():
        output_path, output_exists, unsafe_issue = _inspect_generated_output(
            resolved_project_root,
            output_relative,
            provider,
        )
        if unsafe_issue:
            issues.append(unsafe_issue)
            continue
        if output_exists:
            existing_outputs.append(output_path)
            if provider in declared_provider_set:
                issues.extend(
                    _generated_context_issues(
                        output_path,
                        provider,
                        expected_context_headings,
                        resolved_project_root,
                        _current_provider_fingerprint(root, provider, config),
                    )
                )
        elif provider in declared_provider_set:
            issues.append(
                DoctorIssue(
                    "WARN",
                    "GENERATED_FILE_MISSING",
                    f"Generated provider output is missing for {provider}: {output_relative}",
                    str(output_path),
                    f"Run aos compile {provider} --project-root {resolved_project_root}.",
                )
            )

    scan_targets = _project_security_scan_targets(root, resolved_project_root, existing_outputs)
    issues.extend(_security_issues(scan_private_data(scan_targets)))
    return _project_report(root, resolved_project_root, issues)


def _project_report(root: Path, project_root: Path, issues: list[DoctorIssue]) -> DoctorReport:
    return DoctorReport(
        root=root,
        project_root=project_root,
        ok=not any(issue.severity == "ERROR" for issue in issues),
        issues=issues,
    )


def _invalid_project_config_issue(project_root: Path, detail: str) -> DoctorIssue:
    message = "Project config is invalid"
    if detail:
        message = f"{message}: {detail}"
    return DoctorIssue(
        "ERROR",
        "PROJECT_CONFIG_INVALID",
        message,
        str(project_root / ".agentic-os/project.yaml"),
        "Fix .agentic-os/project.yaml and rerun aos doctor.",
    )


def _security_issues(findings: list[SecurityFinding]) -> list[DoctorIssue]:
    return [
        DoctorIssue(
            "WARN",
            finding.code,
            finding.message,
            finding.path,
            "Remove private data from project files before sharing generated instructions.",
            finding.line,
        )
        for finding in findings
    ]


def _expected_context_headings(root: Path, contexts: list[object]) -> list[str]:
    headings: list[str] = []
    for relative in contexts:
        context_path = resolve_context_path(root, str(relative))
        if context_path.is_file():
            safe_context_file = ensure_readable_file(
                root,
                context_path.relative_to(root),
                "Context file",
            )
            headings.append(_context_heading(safe_context_file, root))
        elif context_path.is_dir():
            for markdown_file in sorted(context_path.glob("*.md")):
                safe_markdown_file = ensure_readable_file(
                    root,
                    markdown_file.relative_to(root),
                    "Context file",
                )
                headings.append(_context_heading(safe_markdown_file, root))
        else:
            raise ValueError(f"Context path is not a file or directory: {relative}")
    return headings


def _context_heading(path: Path, root: Path) -> str:
    return f"### {path.relative_to(root).as_posix()}"


def _generated_context_issues(
    output_path: Path,
    provider: str,
    expected_context_headings: list[str],
    project_root: Path,
    current_fingerprint: str | None,
) -> list[DoctorIssue]:
    try:
        content = output_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        return [
            DoctorIssue(
                "ERROR",
                "GENERATED_FILE_UNREADABLE",
                f"Generated provider output is unreadable for {provider}: {error}",
                str(output_path),
                "Regenerate the provider output with aos compile.",
            )
        ]

    issues: list[DoctorIssue] = []
    for heading in expected_context_headings:
        if heading not in content:
            issues.append(
                DoctorIssue(
                    "WARN",
                    "GENERATED_CONTEXT_MISSING",
                    f"Generated provider output for {provider} is missing context section: {heading[4:]}",
                    str(output_path),
                    f"Run aos compile {provider} --project-root {project_root}.",
                )
            )
    if issues:
        return issues

    if current_fingerprint and extract_context_fingerprint(content) != current_fingerprint:
        issues.append(
            DoctorIssue(
                "WARN",
                "GENERATED_OUTPUT_STALE",
                f"Generated provider output for {provider} is stale.",
                str(output_path),
                f"Run aos compile {provider} --project-root {project_root}.",
            )
        )
    return issues


def _current_provider_fingerprint(
    root: Path,
    provider: str,
    config: dict[str, object],
) -> str | None:
    try:
        return provider_context_fingerprint(root, provider, config)
    except (OSError, UnicodeDecodeError, ValueError):
        return None


def _project_security_scan_targets(
    root: Path,
    project_root: Path,
    existing_outputs: list[Path],
) -> list[Path]:
    project_agentic_os = project_root / ".agentic-os"
    targets = [root, project_agentic_os]
    targets.extend(
        output
        for output in existing_outputs
        if not output.resolve().is_relative_to(project_agentic_os)
    )
    return targets


def _inspect_generated_output(
    project_root: Path,
    relative: str | Path,
    provider: str,
) -> tuple[Path, bool, DoctorIssue | None]:
    target = project_root / Path(relative)
    try:
        relative_path = validate_relative_path(relative)
        target = project_root / relative_path
        reject_symlink_components(project_root, relative_path.parent)
        if target.is_symlink():
            raise ValueError(f"Project file may not be a symlink: {relative_path}")
        _ensure_inside_project_root(project_root, target)
        if not target.exists():
            return target, False, None
        if not target.is_file():
            raise ValueError(f"Project file is not a regular file: {relative_path}")
        if target.stat().st_nlink > 1:
            raise ValueError(f"Project file may not be hardlinked: {relative_path}")
    except (OSError, ValueError) as error:
        return target, True, _generated_file_unsafe_issue(provider, target, error)
    return target, True, None


def _ensure_inside_project_root(project_root: Path, target: Path) -> None:
    if not target.resolve().is_relative_to(project_root):
        raise ValueError(f"Project file escapes project root: {target}")


def _can_write_directory(path: Path) -> bool:
    try:
        with tempfile.TemporaryFile(dir=path):
            return True
    except OSError:
        return False


def _generated_file_unsafe_issue(provider: str, path: Path, detail: Exception) -> DoctorIssue:
    return DoctorIssue(
        "ERROR",
        "GENERATED_FILE_UNSAFE",
        f"Generated provider output is unsafe for {provider}: {detail}",
        str(path),
        "Replace the generated output with a regular file inside the project root.",
    )


def _symlink_component(root: Path, relative: Path) -> Path | None:
    current = root
    relative_current = Path()
    for part in relative.parts:
        current = current / part
        relative_current = relative_current / part
        if current.is_symlink():
            return relative_current
    return None


def render_doctor_json(report: DoctorReport) -> str:
    payload = {
        "ok": report.ok,
        "root": str(report.root),
        "project_root": str(report.project_root) if report.project_root else None,
        "issues": [
            {
                "severity": issue.severity,
                "code": issue.code,
                "message": issue.message,
                "path": issue.path,
                "suggested_action": issue.suggested_action,
                "line": issue.line,
            }
            for issue in report.issues
        ],
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def render_doctor_summary(report: DoctorReport) -> str:
    scope = "project" if report.project_root else "home"
    state = "ok" if report.ok else "issues"
    return f"AOS {scope} {state}: {len(report.errors)} errors, {len(report.warnings)} warnings\n"


def render_doctor_text(report: DoctorReport) -> str:
    if report.ok and not report.issues:
        if report.project_root:
            return f"Agentic OS project is ready at {report.project_root}\n"
        return f"Agentic OS is ready at {report.root}\n"

    lines: list[str] = []
    if report.missing:
        lines.append(f"Missing required paths under {report.root}:")
    elif report.project_root:
        lines.append(f"Agentic OS project diagnostics for {report.project_root}:")
    else:
        lines.append(f"Agentic OS diagnostics for {report.root}:")

    for issue in report.issues:
        lines.append(f"{issue.severity} {issue.code}: {issue.message}")
        lines.append(f"  path: {issue.path}")
        lines.append(f"  action: {issue.suggested_action}")
    return "\n".join(lines) + "\n"
