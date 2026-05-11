import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from agentic_os.bootstrap import init_os
from agentic_os.compiler import compile_provider
from agentic_os.doctor import doctor_os_home, doctor_project, render_doctor_json, render_doctor_text
from agentic_os.memory import add_session_memory
from agentic_os.project import link_project


class DoctorTests(unittest.TestCase):
    def test_os_doctor_reports_ok_after_init(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            init_os(temp_dir)

            report = doctor_os_home(temp_dir)

            self.assertTrue(report.ok)
            self.assertEqual([], report.errors)

    def test_os_doctor_reports_missing_required_file_as_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os_home = init_os(temp_dir)
            (os_home / "providers/codex/AGENTS.template.md").unlink()

            report = doctor_os_home(temp_dir)

            self.assertFalse(report.ok)
            self.assertEqual("MISSING_REQUIRED_FILE", report.errors[0].code)

    def test_os_doctor_reports_symlinked_managed_directory_as_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os_home = init_os(temp_dir)
            outside_dir = Path(temp_dir) / "outside-memory"
            outside_dir.mkdir()
            shutil.rmtree(os_home / "memory/sessions")
            try:
                (os_home / "memory/sessions").symlink_to(outside_dir, target_is_directory=True)
            except (NotImplementedError, OSError) as error:
                self.skipTest(f"Symlink creation is unsupported: {error}")

            report = doctor_os_home(temp_dir)

            self.assertFalse(report.ok)
            self.assertEqual("MANAGED_PATH_SYMLINK", report.errors[0].code)
            self.assertEqual("memory/sessions", report.errors[0].path)

    def test_os_doctor_reports_symlinked_managed_parent_once_with_parent_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os_home = init_os(temp_dir)
            outside_dir = Path(temp_dir) / "outside-core"
            shutil.copytree(os_home / "core", outside_dir)
            shutil.rmtree(os_home / "core")
            try:
                (os_home / "core").symlink_to(outside_dir, target_is_directory=True)
            except (NotImplementedError, OSError) as error:
                self.skipTest(f"Symlink creation is unsupported: {error}")

            report = doctor_os_home(temp_dir)

            self.assertFalse(report.ok)
            symlink_errors = [
                issue for issue in report.errors if issue.code == "MANAGED_PATH_SYMLINK"
            ]
            self.assertEqual(["core"], [issue.path for issue in symlink_errors])

    def test_os_doctor_reports_unwritable_os_home_as_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os_home = init_os(temp_dir)
            os.chmod(os_home, 0o500)
            try:
                report = doctor_os_home(os_home)
            finally:
                os.chmod(os_home, 0o700)

            self.assertFalse(report.ok)
            self.assertIn("OS_HOME_NOT_WRITABLE", [issue.code for issue in report.errors])

    def test_render_doctor_json_is_machine_readable(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            init_os(temp_dir)
            report = doctor_os_home(temp_dir)

            payload = json.loads(render_doctor_json(report))

            self.assertTrue(payload["ok"])
            self.assertEqual([], payload["issues"])

    def test_render_doctor_text_lists_errors(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            report = doctor_os_home(Path(temp_dir) / "missing")

            text = render_doctor_text(report)

            self.assertIn("ERROR", text)
            self.assertIn("MISSING_REQUIRED_DIRECTORY", text)

    def test_project_doctor_reports_missing_project_config(self):
        with tempfile.TemporaryDirectory() as os_dir, tempfile.TemporaryDirectory() as project_dir:
            os_home = init_os(os_dir)

            report = doctor_project(os_home, project_dir)

            self.assertFalse(report.ok)
            self.assertEqual(Path(project_dir).resolve(), report.project_root)
            self.assertEqual(["PROJECT_CONFIG_MISSING"], [issue.code for issue in report.errors])

    def test_project_doctor_reports_unknown_provider_as_invalid_config(self):
        with tempfile.TemporaryDirectory() as os_dir, tempfile.TemporaryDirectory() as project_dir:
            os_home = init_os(os_dir)
            project_root = Path(project_dir)
            link_project(project_root, "demo", "Demo Project", "product", "dai", ["codex"])
            (project_root / ".agentic-os/project.yaml").write_text(
                """id: "demo"
name: "Demo Project"
contexts:
  - core/identity
providers:
  - "unknown"
""",
                encoding="utf-8",
            )

            report = doctor_project(os_home, project_root)

            self.assertFalse(report.ok)
            self.assertEqual(["PROJECT_CONFIG_INVALID"], [issue.code for issue in report.errors])

    def test_project_doctor_reports_inline_scalar_list_sections_as_invalid_config(self):
        with tempfile.TemporaryDirectory() as os_dir, tempfile.TemporaryDirectory() as project_dir:
            os_home = init_os(os_dir)
            project_root = Path(project_dir)
            link_project(project_root, "demo", "Demo Project", "product", "dai", ["codex"])
            (project_root / ".agentic-os/project.yaml").write_text(
                """id: "demo"
name: "Demo Project"
contexts: core/identity
providers: codex
""",
                encoding="utf-8",
            )

            report = doctor_project(os_home, project_root)

            self.assertFalse(report.ok)
            self.assertEqual(["PROJECT_CONFIG_INVALID"], [issue.code for issue in report.errors])

    def test_project_doctor_reports_list_sections_without_dash_items_as_invalid_config(self):
        with tempfile.TemporaryDirectory() as os_dir, tempfile.TemporaryDirectory() as project_dir:
            os_home = init_os(os_dir)
            project_root = Path(project_dir)
            link_project(project_root, "demo", "Demo Project", "product", "dai", ["codex"])
            (project_root / ".agentic-os/project.yaml").write_text(
                """id: "demo"
name: "Demo Project"
contexts:
  core/identity
providers:
  codex
""",
                encoding="utf-8",
            )

            report = doctor_project(os_home, project_root)

            self.assertFalse(report.ok)
            self.assertEqual(["PROJECT_CONFIG_INVALID"], [issue.code for issue in report.errors])

    def test_project_doctor_reports_indentationless_list_items_as_invalid_config(self):
        with tempfile.TemporaryDirectory() as os_dir, tempfile.TemporaryDirectory() as project_dir:
            os_home = init_os(os_dir)
            project_root = Path(project_dir)
            link_project(project_root, "demo", "Demo Project", "product", "dai", ["codex"])
            (project_root / ".agentic-os/project.yaml").write_text(
                """id: "demo"
name: "Demo Project"
contexts:
- core/identity
providers:
- unknown-ai
""",
                encoding="utf-8",
            )

            report = doctor_project(os_home, project_root)

            self.assertFalse(report.ok)
            self.assertEqual(["PROJECT_CONFIG_INVALID"], [issue.code for issue in report.errors])

    def test_project_doctor_reports_missing_context_as_invalid_config(self):
        with tempfile.TemporaryDirectory() as os_dir, tempfile.TemporaryDirectory() as project_dir:
            os_home = init_os(os_dir)
            project_root = Path(project_dir)
            link_project(project_root, "demo", "Demo Project", "product", "dai", ["codex"])
            (project_root / ".agentic-os/project.yaml").write_text(
                """id: "demo"
name: "Demo Project"
contexts:
  - core/missing
providers:
  - "codex"
""",
                encoding="utf-8",
            )

            report = doctor_project(os_home, project_root)

            self.assertFalse(report.ok)
            self.assertEqual(["PROJECT_CONFIG_INVALID"], [issue.code for issue in report.errors])

    def test_project_doctor_reports_symlinked_provider_template_as_error(self):
        with tempfile.TemporaryDirectory() as base_dir:
            base_path = Path(base_dir)
            os_home = init_os(base_path / "os")
            project_root = base_path / "project"
            outside_template = base_path / "outside-template.md"
            outside_template.write_text("private template data\n", encoding="utf-8")
            template_path = os_home / "providers/codex/AGENTS.template.md"
            template_path.unlink()
            try:
                template_path.symlink_to(outside_template)
            except (NotImplementedError, OSError) as error:
                self.skipTest(f"Symlink creation is unsupported: {error}")
            link_project(project_root, "demo", "Demo Project", "product", "dai", ["codex"])

            report = doctor_project(os_home, project_root)

            self.assertFalse(report.ok)
            self.assertIn("PROVIDER_TEMPLATE_UNSAFE", [issue.code for issue in report.errors])

    def test_project_doctor_reports_hardlinked_provider_template_as_error(self):
        with tempfile.TemporaryDirectory() as base_dir:
            base_path = Path(base_dir)
            os_home = init_os(base_path / "os")
            project_root = base_path / "project"
            outside_template = base_path / "outside-template.md"
            outside_template.write_text("private template data\n", encoding="utf-8")
            template_path = os_home / "providers/codex/AGENTS.template.md"
            template_path.unlink()
            try:
                os.link(outside_template, template_path)
            except (NotImplementedError, OSError) as error:
                self.skipTest(f"Hardlink creation is unsupported: {error}")
            link_project(project_root, "demo", "Demo Project", "product", "dai", ["codex"])

            report = doctor_project(os_home, project_root)

            self.assertFalse(report.ok)
            self.assertIn("PROVIDER_TEMPLATE_UNSAFE", [issue.code for issue in report.errors])

    def test_project_doctor_warns_for_missing_generated_provider_file_but_ok(self):
        with tempfile.TemporaryDirectory() as os_dir, tempfile.TemporaryDirectory() as project_dir:
            os_home = init_os(os_dir)
            project_root = Path(project_dir)
            link_project(project_root, "demo", "Demo Project", "product", "dai", ["codex"])

            report = doctor_project(os_home, project_root)

            self.assertTrue(report.ok)
            self.assertEqual([], report.errors)
            self.assertEqual(["GENERATED_FILE_MISSING"], [issue.code for issue in report.warnings])
            self.assertEqual(project_root.resolve(), report.project_root)

    def test_project_doctor_warns_when_generated_output_omits_configured_context(self):
        with tempfile.TemporaryDirectory() as os_dir, tempfile.TemporaryDirectory() as project_dir:
            os_home = init_os(os_dir)
            project_root = Path(project_dir)
            link_project(project_root, "demo", "Demo Project", "product", "dai", ["codex"])
            output_path = compile_provider(os_home, project_root, "codex")
            output_path.write_text(
                output_path.read_text(encoding="utf-8").replace(
                    "### core/identity/user.md",
                    "### omitted-user.md",
                    1,
                ),
                encoding="utf-8",
            )

            report = doctor_project(os_home, project_root)

            self.assertTrue(report.ok)
            missing_context_warnings = [
                issue for issue in report.warnings if issue.code == "GENERATED_CONTEXT_MISSING"
            ]
            self.assertEqual(1, len(missing_context_warnings))
            self.assertEqual(str(output_path.resolve()), missing_context_warnings[0].path)
            self.assertIn("core/identity/user.md", missing_context_warnings[0].message)

    def test_project_doctor_warns_when_generated_output_fingerprint_is_stale(self):
        with tempfile.TemporaryDirectory() as os_dir, tempfile.TemporaryDirectory() as project_dir:
            os_home = init_os(os_dir)
            project_root = Path(project_dir)
            link_project(project_root, "demo", "Demo Project", "product", "dai", ["codex"])
            output_path = compile_provider(os_home, project_root, "codex")
            (os_home / "core/identity/user.md").write_text(
                "# User Identity\nUpdated project context.\n",
                encoding="utf-8",
            )

            report = doctor_project(os_home, project_root)

            self.assertTrue(report.ok)
            stale_warnings = [
                issue for issue in report.warnings if issue.code == "GENERATED_OUTPUT_STALE"
            ]
            self.assertEqual(1, len(stale_warnings))
            self.assertEqual(str(output_path.resolve()), stale_warnings[0].path)
            self.assertIn("codex", stale_warnings[0].message)

    def test_project_doctor_warns_when_recent_memory_makes_generated_output_stale(self):
        with tempfile.TemporaryDirectory() as os_dir, tempfile.TemporaryDirectory() as project_dir:
            os_home = init_os(os_dir)
            project_root = Path(project_dir)
            link_project(project_root, "demo", "Demo Project", "product", "dai", ["codex"])
            output_path = compile_provider(os_home, project_root, "codex")
            add_session_memory(
                os_home,
                "demo",
                "New Memory",
                "This memory should require regeneration.",
                timestamp="2026-05-11 10:00",
            )

            report = doctor_project(os_home, project_root)

            stale_warnings = [
                issue for issue in report.warnings if issue.code == "GENERATED_OUTPUT_STALE"
            ]
            self.assertEqual(1, len(stale_warnings))
            self.assertEqual(str(output_path.resolve()), stale_warnings[0].path)

    def test_project_doctor_scans_project_agentic_os_and_os_home_for_private_data(self):
        with tempfile.TemporaryDirectory() as os_dir, tempfile.TemporaryDirectory() as project_dir:
            os_home = init_os(os_dir)
            project_root = Path(project_dir)
            link_project(project_root, "demo", "Demo Project", "product", "dai", ["codex"])
            os_env = os_home / ".env.local"
            os_env.write_text("DEBUG=true\n", encoding="utf-8")
            project_env = project_root / ".agentic-os/.env.local"
            project_env.write_text("DEBUG=true\n", encoding="utf-8")

            report = doctor_project(os_home, project_root)

            warning_pairs = [(issue.code, issue.path) for issue in report.warnings]
            self.assertIn(("SENSITIVE_FILENAME", str(os_env)), warning_pairs)
            self.assertIn(("SENSITIVE_FILENAME", str(project_env.resolve())), warning_pairs)
            self.assertNotIn(
                (
                    "PRIVATE_MEMORY_REFERENCE",
                    str((project_root / ".agentic-os/project.yaml").resolve()),
                ),
                warning_pairs,
            )

    def test_project_doctor_reports_symlinked_generated_provider_output_as_error(self):
        with tempfile.TemporaryDirectory() as base_dir:
            base_path = Path(base_dir)
            os_home = init_os(base_path / "os")
            project_root = base_path / "project"
            outside_file = base_path / "outside-agents.md"
            outside_file.write_text("outside agents\n", encoding="utf-8")
            link_project(project_root, "demo", "Demo Project", "product", "dai", ["codex"])
            try:
                (project_root / "AGENTS.md").symlink_to(outside_file)
            except (NotImplementedError, OSError) as error:
                self.skipTest(f"Symlink creation is unsupported: {error}")

            report = doctor_project(os_home, project_root)

            self.assertFalse(report.ok)
            self.assertEqual(["GENERATED_FILE_UNSAFE"], [issue.code for issue in report.errors])
            self.assertIn("symlink", report.errors[0].message)

    def test_project_doctor_reports_hardlinked_generated_provider_output_as_error(self):
        with tempfile.TemporaryDirectory() as base_dir:
            base_path = Path(base_dir)
            os_home = init_os(base_path / "os")
            project_root = base_path / "project"
            outside_file = base_path / "outside-agents.md"
            outside_file.write_text("outside agents\n", encoding="utf-8")
            link_project(project_root, "demo", "Demo Project", "product", "dai", ["codex"])
            try:
                os.link(outside_file, project_root / "AGENTS.md")
            except (NotImplementedError, OSError) as error:
                self.skipTest(f"Hardlink creation is unsupported: {error}")

            report = doctor_project(os_home, project_root)

            self.assertFalse(report.ok)
            self.assertEqual(["GENERATED_FILE_UNSAFE"], [issue.code for issue in report.errors])
            self.assertIn("hardlinked", report.errors[0].message)
            self.assertEqual("outside agents\n", outside_file.read_text(encoding="utf-8"))

    def test_project_doctor_scans_stale_known_provider_outputs(self):
        with tempfile.TemporaryDirectory() as os_dir, tempfile.TemporaryDirectory() as project_dir:
            os_home = init_os(os_dir)
            project_root = Path(project_dir)
            link_project(project_root, "demo", "Demo Project", "product", "dai", ["codex"])
            stale_output = project_root / "CLAUDE.md"
            stale_output.write_text("Stale path /Users/dai/private-notes.md\n", encoding="utf-8")

            report = doctor_project(os_home, project_root)

            self.assertTrue(report.ok)
            self.assertIn("LOCAL_PATH_PATTERN", [issue.code for issue in report.warnings])
            stale_findings = [
                issue
                for issue in report.warnings
                if issue.code == "LOCAL_PATH_PATTERN" and issue.path == str(stale_output.resolve())
            ]
            self.assertEqual([1], [issue.line for issue in stale_findings])

    def test_render_doctor_json_preserves_security_finding_line(self):
        with tempfile.TemporaryDirectory() as os_dir, tempfile.TemporaryDirectory() as project_dir:
            os_home = init_os(os_dir)
            project_root = Path(project_dir)
            link_project(project_root, "demo", "Demo Project", "product", "dai", ["codex"])
            output_path = project_root / "AGENTS.md"
            output_path.write_text("Generated\nOPENAI_API_KEY=abc\n", encoding="utf-8")

            payload = json.loads(render_doctor_json(doctor_project(os_home, project_root)))

            secret_issues = [
                issue for issue in payload["issues"] if issue["code"] == "SECRET_PATTERN"
            ]
            self.assertEqual([2], [issue["line"] for issue in secret_issues])
