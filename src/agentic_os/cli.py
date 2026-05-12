import argparse
import contextlib
import sys
from typing import Sequence, TextIO

from .bootstrap import init_os
from .compiler import compile_provider
from .distribution import (
    distribution_check,
    render_distribution_check_json,
    render_distribution_check_summary,
)
from .doctor import (
    doctor_os_home,
    doctor_project,
    render_doctor_json,
    render_doctor_summary,
    render_doctor_text,
)
from .fresh_user_smoke import (
    fresh_user_smoke,
    render_fresh_user_smoke_json,
    render_fresh_user_smoke_summary,
)
from .memory import add_decision_memory, add_session_memory
from .memory_index import list_memory, search_memory
from .onboarding_check import (
    onboarding_check,
    render_onboarding_check_json,
    render_onboarding_check_summary,
)
from .project import link_project
from .readiness import readiness_project, render_readiness_json, render_readiness_summary
from .release_check import (
    release_check,
    render_release_check_json,
    render_release_check_summary,
)
from .release_upgrade_smoke import (
    release_upgrade_smoke,
    render_release_upgrade_smoke_json,
    render_release_upgrade_smoke_summary,
)
from .public_audit import public_audit, render_public_audit_json, render_public_audit_summary
from .public_export import public_export, render_public_export_json, render_public_export_summary
from .public_release_gate import (
    public_release_gate,
    render_public_release_gate_json,
    render_public_release_gate_summary,
)
from .scaffold import create_skill, create_workflow
from .self_check import self_check, render_self_check_json, render_self_check_summary
from .version import collect_version_info, render_version_json, render_version_text


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aos",
        description="Local file-based Agentic OS",
    )
    parser.add_argument(
        "--os-home",
        help="Agentic OS home folder. Defaults to AGENTIC_OS_HOME or ~/.agentic-os.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)
    version_parser = subparsers.add_parser("version", help="Show AOS version and runtime traceability.")
    version_parser.add_argument("--json", action="store_true", dest="as_json")
    subparsers.add_parser("init", help="Create the global Agentic OS folder.")
    doctor_parser = subparsers.add_parser("doctor", help="Validate the Agentic OS folder.")
    doctor_parser.add_argument("--project-root")
    doctor_output_group = doctor_parser.add_mutually_exclusive_group()
    doctor_output_group.add_argument("--json", action="store_true", dest="as_json")
    doctor_output_group.add_argument("--summary", action="store_true")
    readiness_parser = subparsers.add_parser(
        "readiness",
        help="Check whether a linked project is ready for daily Agentic OS use.",
    )
    readiness_parser.add_argument("--project-root", required=True)
    readiness_parser.add_argument("--json", action="store_true", dest="as_json")
    self_check_parser = subparsers.add_parser(
        "self-check",
        help="Check global Agentic OS installation and current project readiness.",
    )
    self_check_parser.add_argument("--project-root", default=".")
    self_check_parser.add_argument("--json", action="store_true", dest="as_json")
    onboarding_check_parser = subparsers.add_parser(
        "onboarding-check",
        help="Compile provider outputs and run distribution readiness checks.",
    )
    onboarding_check_parser.add_argument("--project-root", default=".")
    onboarding_check_parser.add_argument("--json", action="store_true", dest="as_json")
    distribution_check_parser = subparsers.add_parser(
        "distribution-check",
        help="Check whether this repository is safe to share as an AOS package.",
    )
    distribution_check_parser.add_argument("--repo-root", default=".")
    distribution_check_parser.add_argument("--json", action="store_true", dest="as_json")
    release_check_parser = subparsers.add_parser(
        "release-check",
        help="Run the full standalone AOS pre-release gate.",
    )
    release_check_parser.add_argument("--repo-root", default=".")
    release_check_parser.add_argument("--launcher")
    release_check_parser.add_argument(
        "--skip-release-manifest",
        action="store_true",
        help="Skip the generated release manifest checksum gate.",
    )
    release_check_parser.add_argument("--fresh-user-smoke", action="store_true")
    release_check_parser.add_argument("--upgrade-smoke", action="store_true")
    release_check_parser.add_argument("--from-ref")
    release_check_parser.add_argument("--to-ref", default="HEAD")
    release_check_parser.add_argument("--json", action="store_true", dest="as_json")
    fresh_user_smoke_parser = subparsers.add_parser(
        "fresh-user-smoke",
        help="Verify a first-user install, project link, provider compile, and onboarding flow.",
    )
    fresh_user_smoke_parser.add_argument("--repo-root", default=".")
    fresh_user_smoke_parser.add_argument("--launcher")
    fresh_user_smoke_parser.add_argument("--json", action="store_true", dest="as_json")
    release_upgrade_smoke_parser = subparsers.add_parser(
        "release-upgrade-smoke",
        help="Verify install, update, and rollback between two release refs.",
    )
    release_upgrade_smoke_parser.add_argument("--repo-root", default=".")
    release_upgrade_smoke_parser.add_argument("--from-ref", required=True)
    release_upgrade_smoke_parser.add_argument("--to-ref", default="HEAD")
    release_upgrade_smoke_parser.add_argument("--json", action="store_true", dest="as_json")
    public_audit_parser = subparsers.add_parser(
        "public-audit",
        help="Scan the current tree and git history for public-release privacy risks.",
    )
    public_audit_parser.add_argument("--repo-root", default=".")
    public_audit_parser.add_argument(
        "--tree-only",
        action="store_true",
        help="Scan only the current tree and skip git history.",
    )
    public_audit_parser.add_argument("--json", action="store_true", dest="as_json")
    public_export_parser = subparsers.add_parser(
        "public-export",
        help="Create a clean public-release snapshot from the standalone repository.",
    )
    public_export_parser.add_argument("--repo-root", default=".")
    public_export_parser.add_argument("--output", required=True)
    public_export_parser.add_argument("--force", action="store_true")
    public_export_parser.add_argument("--json", action="store_true", dest="as_json")
    public_release_gate_parser = subparsers.add_parser(
        "public-release-gate",
        help="Run the canonical public release gate with audit, manifest, fresh-user, and upgrade checks.",
    )
    public_release_gate_parser.add_argument("--repo-root", default=".")
    public_release_gate_parser.add_argument("--launcher")
    public_release_gate_parser.add_argument("--from-ref")
    public_release_gate_parser.add_argument("--to-ref", default="HEAD")
    public_release_gate_parser.add_argument(
        "--tree-only",
        action="store_true",
        help="Development/CI only: skip git history audit and scan only the current tree.",
    )
    public_release_gate_parser.add_argument("--json", action="store_true", dest="as_json")
    link_project_parser = subparsers.add_parser(
        "link-project",
        help="Create a project Agentic OS config.",
    )
    link_project_parser.add_argument("--project-root", required=True)
    link_project_parser.add_argument("--id", dest="project_id", required=True)
    link_project_parser.add_argument("--name", required=True)
    link_project_parser.add_argument("--type", dest="project_type", default="project")
    link_project_parser.add_argument("--owner", default="dai")
    link_project_parser.add_argument(
        "--provider",
        dest="providers",
        action="append",
        default=[],
    )
    compile_parser = subparsers.add_parser(
        "compile",
        help="Compile provider instructions for a linked project.",
    )
    compile_parser.add_argument(
        "provider",
        choices=["codex", "claude", "gemini", "chatgpt"],
    )
    compile_parser.add_argument("--project-root", required=True)
    memory_parser = subparsers.add_parser("memory", help="Record Agentic OS memory.")
    memory_subparsers = memory_parser.add_subparsers(dest="memory_command", required=True)
    memory_list_parser = memory_subparsers.add_parser("list", help="List memory entries.")
    memory_list_parser.add_argument("--project-id")
    memory_list_parser.add_argument("--type", dest="memory_filter_type")
    memory_list_parser.add_argument("--limit", type=int)
    memory_search_parser = memory_subparsers.add_parser("search", help="Search memory entries.")
    memory_search_parser.add_argument("query")
    memory_search_parser.add_argument("--project-id")
    memory_add_parser = memory_subparsers.add_parser("add", help="Add a memory entry.")
    memory_add_subparsers = memory_add_parser.add_subparsers(dest="memory_type", required=True)
    session_parser = memory_add_subparsers.add_parser("session", help="Add session memory.")
    session_parser.add_argument("--project-id", required=True)
    session_parser.add_argument("--title", required=True)
    session_parser.add_argument("--summary", required=True)
    session_parser.add_argument("--next-action", action="append", dest="next_actions", default=[])
    session_parser.add_argument("--timestamp")
    session_parser.add_argument("--tag", action="append", dest="tags", default=[])
    session_parser.add_argument("--decision", action="append", dest="decisions", default=[])
    session_parser.add_argument("--artifact", action="append", dest="artifacts", default=[])
    decision_parser = memory_add_subparsers.add_parser("decision", help="Add decision memory.")
    decision_parser.add_argument("--project-id", required=True)
    decision_parser.add_argument("--title", required=True)
    decision_parser.add_argument("--rationale", required=True)
    decision_parser.add_argument("--timestamp")
    skill_parser = subparsers.add_parser("skill", help="Manage skills.")
    skill_subparsers = skill_parser.add_subparsers(dest="skill_command", required=True)
    skill_create_parser = skill_subparsers.add_parser("create", help="Create a skill scaffold.")
    skill_create_parser.add_argument("skill_id")
    skill_create_parser.add_argument("--name", required=True)

    workflow_parser = subparsers.add_parser("workflow", help="Manage workflows.")
    workflow_subparsers = workflow_parser.add_subparsers(dest="workflow_command", required=True)
    workflow_create_parser = workflow_subparsers.add_parser("create", help="Create a workflow scaffold.")
    workflow_create_parser.add_argument("workflow_id")
    workflow_create_parser.add_argument("--name", required=True)
    return parser


def main(
    argv: Sequence[str] | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    stdout = stdout or sys.stdout
    stderr = stderr or sys.stderr
    parser = build_parser()
    try:
        with contextlib.redirect_stderr(stderr):
            args = parser.parse_args(argv)
    except SystemExit as error:
        return int(error.code)

    try:
        if args.command == "version":
            info = collect_version_info(args.os_home)
            if args.as_json:
                stdout.write(render_version_json(info))
            else:
                stdout.write(render_version_text(info))
            return 0

        if args.command == "init":
            root = init_os(args.os_home)
            stdout.write(f"Initialized Agentic OS at {root}\n")
            return 0

        if args.command == "doctor":
            if args.project_root:
                report = doctor_project(args.os_home, args.project_root)
            else:
                report = doctor_os_home(args.os_home)
            if args.as_json:
                stdout.write(render_doctor_json(report))
            elif args.summary:
                stdout.write(render_doctor_summary(report))
            else:
                stdout.write(render_doctor_text(report))
            return 0 if report.ok else 1

        if args.command == "readiness":
            report = readiness_project(args.os_home, args.project_root)
            if args.as_json:
                stdout.write(render_readiness_json(report))
            else:
                stdout.write(render_readiness_summary(report))
            return 0 if report.ok else 1

        if args.command == "self-check":
            report = self_check(args.os_home, args.project_root)
            if args.as_json:
                stdout.write(render_self_check_json(report))
            else:
                stdout.write(render_self_check_summary(report))
            return 0 if report.ok else 1

        if args.command == "onboarding-check":
            report = onboarding_check(args.os_home, args.project_root)
            if args.as_json:
                stdout.write(render_onboarding_check_json(report))
            else:
                stdout.write(render_onboarding_check_summary(report))
            return 0 if report.ok else 1

        if args.command == "distribution-check":
            report = distribution_check(args.repo_root)
            if args.as_json:
                stdout.write(render_distribution_check_json(report))
            else:
                stdout.write(render_distribution_check_summary(report))
            return 0 if report.ok else 1

        if args.command == "release-check":
            report = release_check(
                args.repo_root,
                args.launcher,
                release_manifest_gate=not args.skip_release_manifest,
                fresh_user_smoke_gate=args.fresh_user_smoke,
                upgrade_smoke=args.upgrade_smoke,
                from_ref=args.from_ref,
                to_ref=args.to_ref,
            )
            if args.as_json:
                stdout.write(render_release_check_json(report))
            else:
                stdout.write(render_release_check_summary(report))
            return 0 if report.ok else 1

        if args.command == "fresh-user-smoke":
            report = fresh_user_smoke(args.repo_root, args.launcher)
            if args.as_json:
                stdout.write(render_fresh_user_smoke_json(report))
            else:
                stdout.write(render_fresh_user_smoke_summary(report))
            return 0 if report.ok else 1

        if args.command == "release-upgrade-smoke":
            report = release_upgrade_smoke(args.repo_root, args.from_ref, args.to_ref)
            if args.as_json:
                stdout.write(render_release_upgrade_smoke_json(report))
            else:
                stdout.write(render_release_upgrade_smoke_summary(report))
            return 0 if report.ok else 1

        if args.command == "public-audit":
            report = public_audit(args.repo_root, include_history=not args.tree_only)
            if args.as_json:
                stdout.write(render_public_audit_json(report))
            else:
                stdout.write(render_public_audit_summary(report))
            return 0 if report.ok else 1

        if args.command == "public-export":
            manifest = public_export(args.repo_root, args.output, force=args.force)
            if args.as_json:
                stdout.write(render_public_export_json(manifest))
            else:
                stdout.write(render_public_export_summary(manifest))
            return 0

        if args.command == "public-release-gate":
            report = public_release_gate(
                args.repo_root,
                args.launcher,
                from_ref=args.from_ref,
                to_ref=args.to_ref,
                include_history=not args.tree_only,
            )
            if args.as_json:
                stdout.write(render_public_release_gate_json(report))
            else:
                stdout.write(render_public_release_gate_summary(report))
            return 0 if report.ok else 1

        if args.command == "link-project":
            providers = args.providers or ["codex", "claude"]
            config_path = link_project(
                args.project_root,
                args.project_id,
                args.name,
                args.project_type,
                args.owner,
                providers,
            )
            stdout.write(f"Linked project at {config_path}\n")
            return 0

        if args.command == "compile":
            output_path = compile_provider(args.os_home, args.project_root, args.provider)
            stdout.write(f"Compiled {args.provider} instructions to {output_path}\n")
            return 0

        if args.command == "memory" and args.memory_command == "list":
            entries = list_memory(
                args.os_home,
                project_id=args.project_id,
                memory_type=args.memory_filter_type,
                limit=args.limit,
            )
            for entry in entries:
                _write_tsv(
                    stdout,
                    [
                        entry.timestamp,
                        entry.memory_type,
                        entry.project_id,
                        entry.title,
                        str(entry.path),
                    ]
                )
            return 0

        if args.command == "memory" and args.memory_command == "search":
            results = search_memory(args.os_home, args.query, project_id=args.project_id)
            for result in results:
                _write_tsv(
                    stdout,
                    [
                        result.timestamp,
                        result.memory_type,
                        result.project_id,
                        result.title,
                        str(result.path),
                        result.snippet,
                    ]
                )
            return 0

        if args.command == "memory" and args.memory_command == "add" and args.memory_type == "session":
            session_path = add_session_memory(
                args.os_home,
                args.project_id,
                args.title,
                args.summary,
                args.next_actions,
                args.timestamp,
                tags=args.tags,
                decisions=args.decisions,
                artifacts=args.artifacts,
            )
            stdout.write(f"Recorded session memory at {session_path}\n")
            return 0

        if args.command == "memory" and args.memory_command == "add" and args.memory_type == "decision":
            decision_path = add_decision_memory(
                args.os_home,
                args.project_id,
                args.title,
                args.rationale,
                args.timestamp,
            )
            stdout.write(f"Recorded decision memory at {decision_path}\n")
            return 0

        if args.command == "skill" and args.skill_command == "create":
            skill_dir = create_skill(args.os_home, args.skill_id, args.name)
            stdout.write(f"Created skill at {skill_dir}\n")
            return 0

        if args.command == "workflow" and args.workflow_command == "create":
            workflow_dir = create_workflow(args.os_home, args.workflow_id, args.name)
            stdout.write(f"Created workflow at {workflow_dir}\n")
            return 0
    except (OSError, ValueError) as error:
        stderr.write(f"Error: {error}\n")
        return 1

    stderr.write(f"Unknown command: {args.command}\n")
    return 2


def _write_tsv(stdout: TextIO, fields: Sequence[object]) -> None:
    stdout.write("\t".join(_escape_tsv_field(field) for field in fields) + "\n")


def _escape_tsv_field(field: object) -> str:
    return str(field).replace("\t", "\\t").replace("\r", "\\r").replace("\n", "\\n")
