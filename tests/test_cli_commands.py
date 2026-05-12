import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agentic_os.cli import main
from agentic_os.project import link_project


class CliCommandTests(unittest.TestCase):
    def test_init_command_creates_os_home(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            stdout = io.StringIO()
            code = main(["--os-home", temp_dir, "init"], stdout=stdout)

            self.assertEqual(code, 0)
            self.assertIn("Initialized Agentic OS", stdout.getvalue())

    def test_init_command_returns_nonzero_for_file_home(self):
        with tempfile.NamedTemporaryFile() as temp_file:
            stdout = io.StringIO()
            stderr = io.StringIO()
            code = main(
                ["--os-home", temp_file.name, "init"],
                stdout=stdout,
                stderr=stderr,
            )

            self.assertEqual(code, 1)
            self.assertIn("Error:", stderr.getvalue())

    def test_version_command_reports_traceability_summary(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            stdout = io.StringIO()

            code = main(["--os-home", temp_dir, "version"], stdout=stdout)

            output = stdout.getvalue()
            self.assertEqual(0, code)
            self.assertIn("AOS version 0.1.9", output)
            self.assertIn("Release channel: public-alpha", output)
            self.assertIn("Release tag: v0.1.9-public-alpha", output)
            self.assertIn("Python executable:", output)
            self.assertIn("Command path:", output)
            self.assertIn(f"OS home: {Path(temp_dir).resolve()}", output)

    def test_version_command_outputs_json(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            stdout = io.StringIO()

            code = main(["--os-home", temp_dir, "version", "--json"], stdout=stdout)

            self.assertEqual(0, code)
            payload = json.loads(stdout.getvalue())
            self.assertEqual("0.1.9", payload["version"])
            self.assertEqual("public-alpha", payload["release_channel"])
            self.assertEqual("v0.1.9-public-alpha", payload["release_tag"])
            self.assertEqual(str(Path(temp_dir).resolve()), payload["os_home"])
            self.assertIn("python_version", payload)
            self.assertIn("python_executable", payload)
            self.assertIn("command_path", payload)

    def test_version_command_prefers_launcher_command_path_env(self):
        with tempfile.NamedTemporaryFile() as launcher_file:
            stdout = io.StringIO()

            with patch.dict(os.environ, {"AOS_COMMAND_PATH": launcher_file.name}):
                code = main(["version", "--json"], stdout=stdout)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(0, code)
            self.assertEqual(str(Path(launcher_file.name).resolve()), payload["command_path"])

    def test_doctor_command_passes_after_init(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.assertEqual(main(["--os-home", temp_dir, "init"], stdout=io.StringIO()), 0)

            stdout = io.StringIO()
            code = main(["--os-home", temp_dir, "doctor"], stdout=stdout)

            self.assertEqual(code, 0)
            self.assertIn("Agentic OS is ready", stdout.getvalue())

    def test_doctor_command_returns_nonzero_for_missing_home(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            missing = f"{temp_dir}/missing-os"
            stdout = io.StringIO()
            code = main(["--os-home", missing, "doctor"], stdout=stdout)

            self.assertEqual(code, 1)
            self.assertIn("Missing required paths", stdout.getvalue())

    def test_doctor_command_outputs_json(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.assertEqual(main(["--os-home", temp_dir, "init"], stdout=io.StringIO()), 0)
            stdout = io.StringIO()

            code = main(["--os-home", temp_dir, "doctor", "--json"], stdout=stdout)

            self.assertEqual(0, code)
            self.assertIn('"ok": true', stdout.getvalue())

    def test_doctor_command_returns_one_for_errors(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            stdout = io.StringIO()

            code = main(["--os-home", f"{temp_dir}/missing", "doctor", "--json"], stdout=stdout)

            self.assertEqual(1, code)
            self.assertIn('"ok": false', stdout.getvalue())

    def test_doctor_project_json_returns_zero_for_warnings_only(self):
        with tempfile.TemporaryDirectory() as os_dir, tempfile.TemporaryDirectory() as project_dir:
            self.assertEqual(main(["--os-home", os_dir, "init"], stdout=io.StringIO()), 0)
            project_root = Path(project_dir)
            link_project(project_root, "demo", "Demo Project", "product", "dai", ["codex"])
            stdout = io.StringIO()

            code = main(
                ["--os-home", os_dir, "doctor", "--project-root", str(project_root), "--json"],
                stdout=stdout,
            )

            payload = json.loads(stdout.getvalue())
            self.assertEqual(0, code)
            self.assertTrue(payload["ok"])
            self.assertEqual(str(project_root.resolve()), payload["project_root"])
            self.assertEqual(["GENERATED_FILE_MISSING"], [issue["code"] for issue in payload["issues"]])

    def test_doctor_project_summary_counts_warnings(self):
        with tempfile.TemporaryDirectory() as os_dir, tempfile.TemporaryDirectory() as project_dir:
            self.assertEqual(main(["--os-home", os_dir, "init"], stdout=io.StringIO()), 0)
            project_root = Path(project_dir)
            link_project(project_root, "demo", "Demo Project", "product", "dai", ["codex"])
            stdout = io.StringIO()

            code = main(
                ["--os-home", os_dir, "doctor", "--project-root", str(project_root), "--summary"],
                stdout=stdout,
            )

            self.assertEqual(0, code)
            self.assertEqual("AOS project ok: 0 errors, 1 warnings\n", stdout.getvalue())

    def test_doctor_project_summary_reports_clean_project(self):
        with tempfile.TemporaryDirectory() as os_dir, tempfile.TemporaryDirectory() as project_dir:
            self.assertEqual(main(["--os-home", os_dir, "init"], stdout=io.StringIO()), 0)
            project_root = Path(project_dir)
            link_project(project_root, "demo", "Demo Project", "product", "dai", ["codex"])
            self.assertEqual(
                main(
                    ["--os-home", os_dir, "compile", "codex", "--project-root", str(project_root)],
                    stdout=io.StringIO(),
                ),
                0,
            )
            stdout = io.StringIO()

            code = main(
                ["--os-home", os_dir, "doctor", "--project-root", str(project_root), "--summary"],
                stdout=stdout,
            )

            self.assertEqual(0, code)
            self.assertEqual("AOS project ok: 0 errors, 0 warnings\n", stdout.getvalue())

    def test_readiness_command_reports_clean_project_ready(self):
        with tempfile.TemporaryDirectory() as os_dir, tempfile.TemporaryDirectory() as project_dir:
            self.assertEqual(main(["--os-home", os_dir, "init"], stdout=io.StringIO()), 0)
            project_root = Path(project_dir)
            link_project(project_root, "demo", "Demo Project", "product", "dai", ["codex"])
            self.assertEqual(
                main(
                    ["--os-home", os_dir, "compile", "codex", "--project-root", str(project_root)],
                    stdout=io.StringIO(),
                ),
                0,
            )
            stdout = io.StringIO()

            code = main(
                ["--os-home", os_dir, "readiness", "--project-root", str(project_root)],
                stdout=stdout,
            )

            self.assertEqual(0, code)
            self.assertEqual(
                "AOS readiness ok: 0 errors, 0 warnings, 1 providers, memory ok\n",
                stdout.getvalue(),
            )

    def test_readiness_command_outputs_json_for_clean_project(self):
        with tempfile.TemporaryDirectory() as os_dir, tempfile.TemporaryDirectory() as project_dir:
            self.assertEqual(main(["--os-home", os_dir, "init"], stdout=io.StringIO()), 0)
            project_root = Path(project_dir)
            link_project(project_root, "demo", "Demo Project", "product", "dai", ["codex"])
            self.assertEqual(
                main(
                    ["--os-home", os_dir, "compile", "codex", "--project-root", str(project_root)],
                    stdout=io.StringIO(),
                ),
                0,
            )
            stdout = io.StringIO()

            code = main(
                ["--os-home", os_dir, "readiness", "--project-root", str(project_root), "--json"],
                stdout=stdout,
            )

            payload = json.loads(stdout.getvalue())
            self.assertEqual(0, code)
            self.assertTrue(payload["ok"])
            self.assertEqual(str(Path(os_dir).resolve()), payload["os_home"])
            self.assertEqual(str(project_root.resolve()), payload["project_root"])
            self.assertEqual("demo", payload["project_id"])
            self.assertEqual(1, payload["providers_count"])
            self.assertTrue(payload["memory_ok"])
            self.assertEqual(0, payload["errors_count"])
            self.assertEqual(0, payload["warnings_count"])
            self.assertEqual([], payload["issues"])

    def test_readiness_command_returns_one_for_project_warnings(self):
        with tempfile.TemporaryDirectory() as os_dir, tempfile.TemporaryDirectory() as project_dir:
            self.assertEqual(main(["--os-home", os_dir, "init"], stdout=io.StringIO()), 0)
            project_root = Path(project_dir)
            link_project(project_root, "demo", "Demo Project", "product", "dai", ["codex"])
            stdout = io.StringIO()

            code = main(
                ["--os-home", os_dir, "readiness", "--project-root", str(project_root)],
                stdout=stdout,
            )

            self.assertEqual(1, code)
            self.assertEqual(
                "AOS readiness issues: 0 errors, 1 warnings, 1 providers, memory ok\n",
                stdout.getvalue(),
            )

    def test_readiness_json_returns_one_for_project_warnings(self):
        with tempfile.TemporaryDirectory() as os_dir, tempfile.TemporaryDirectory() as project_dir:
            self.assertEqual(main(["--os-home", os_dir, "init"], stdout=io.StringIO()), 0)
            project_root = Path(project_dir)
            link_project(project_root, "demo", "Demo Project", "product", "dai", ["codex"])
            stdout = io.StringIO()

            code = main(
                ["--os-home", os_dir, "readiness", "--project-root", str(project_root), "--json"],
                stdout=stdout,
            )

            payload = json.loads(stdout.getvalue())
            self.assertEqual(1, code)
            self.assertFalse(payload["ok"])
            self.assertEqual(0, payload["errors_count"])
            self.assertEqual(1, payload["warnings_count"])
            self.assertEqual(1, payload["providers_count"])
            self.assertTrue(payload["memory_ok"])
            self.assertEqual(["GENERATED_FILE_MISSING"], [issue["code"] for issue in payload["issues"]])

    def test_readiness_json_returns_one_when_generated_output_omits_configured_context(self):
        with tempfile.TemporaryDirectory() as os_dir, tempfile.TemporaryDirectory() as project_dir:
            self.assertEqual(main(["--os-home", os_dir, "init"], stdout=io.StringIO()), 0)
            project_root = Path(project_dir)
            link_project(project_root, "demo", "Demo Project", "product", "dai", ["codex"])
            self.assertEqual(
                main(
                    ["--os-home", os_dir, "compile", "codex", "--project-root", str(project_root)],
                    stdout=io.StringIO(),
                ),
                0,
            )
            output_path = project_root / "AGENTS.md"
            output_path.write_text(
                output_path.read_text(encoding="utf-8").replace(
                    "### core/identity/user.md",
                    "### omitted-user.md",
                    1,
                ),
                encoding="utf-8",
            )
            stdout = io.StringIO()

            code = main(
                ["--os-home", os_dir, "readiness", "--project-root", str(project_root), "--json"],
                stdout=stdout,
            )

            payload = json.loads(stdout.getvalue())
            self.assertEqual(1, code)
            self.assertFalse(payload["ok"])
            self.assertEqual(1, payload["warnings_count"])
            self.assertEqual(["GENERATED_CONTEXT_MISSING"], [issue["code"] for issue in payload["issues"]])

    def test_readiness_json_returns_one_when_generated_output_fingerprint_is_stale(self):
        with tempfile.TemporaryDirectory() as os_dir, tempfile.TemporaryDirectory() as project_dir:
            self.assertEqual(main(["--os-home", os_dir, "init"], stdout=io.StringIO()), 0)
            project_root = Path(project_dir)
            link_project(project_root, "demo", "Demo Project", "product", "dai", ["codex"])
            self.assertEqual(
                main(
                    ["--os-home", os_dir, "compile", "codex", "--project-root", str(project_root)],
                    stdout=io.StringIO(),
                ),
                0,
            )
            (Path(os_dir) / "core/identity/user.md").write_text(
                "# User Identity\nUpdated project context.\n",
                encoding="utf-8",
            )
            stdout = io.StringIO()

            code = main(
                ["--os-home", os_dir, "readiness", "--project-root", str(project_root), "--json"],
                stdout=stdout,
            )

            payload = json.loads(stdout.getvalue())
            self.assertEqual(1, code)
            self.assertFalse(payload["ok"])
            self.assertEqual(1, payload["warnings_count"])
            self.assertEqual(["GENERATED_OUTPUT_STALE"], [issue["code"] for issue in payload["issues"]])

    def test_self_check_command_reports_clean_environment(self):
        with tempfile.TemporaryDirectory() as os_dir, tempfile.TemporaryDirectory() as project_dir:
            self.assertEqual(main(["--os-home", os_dir, "init"], stdout=io.StringIO()), 0)
            project_root = Path(project_dir)
            link_project(project_root, "demo", "Demo Project", "product", "dai", ["codex"])
            self.assertEqual(
                main(
                    ["--os-home", os_dir, "compile", "codex", "--project-root", str(project_root)],
                    stdout=io.StringIO(),
                ),
                0,
            )
            stdout = io.StringIO()

            with patch("agentic_os.self_check.shutil.which", return_value="/tmp/bin/aos"):
                code = main(
                    ["--os-home", os_dir, "self-check", "--project-root", str(project_root)],
                    stdout=stdout,
                )

            self.assertEqual(0, code)
            self.assertEqual(
                "AOS self-check ok: 3 passed, 0 failed\n",
                stdout.getvalue(),
            )

    def test_self_check_command_outputs_json(self):
        with tempfile.TemporaryDirectory() as os_dir, tempfile.TemporaryDirectory() as project_dir:
            self.assertEqual(main(["--os-home", os_dir, "init"], stdout=io.StringIO()), 0)
            project_root = Path(project_dir)
            link_project(project_root, "demo", "Demo Project", "product", "dai", ["codex"])
            self.assertEqual(
                main(
                    ["--os-home", os_dir, "compile", "codex", "--project-root", str(project_root)],
                    stdout=io.StringIO(),
                ),
                0,
            )
            stdout = io.StringIO()

            with patch("agentic_os.self_check.shutil.which", return_value="/tmp/bin/aos"):
                code = main(
                    ["--os-home", os_dir, "self-check", "--project-root", str(project_root), "--json"],
                    stdout=stdout,
                )

            payload = json.loads(stdout.getvalue())
            self.assertEqual(0, code)
            self.assertTrue(payload["ok"])
            self.assertEqual(3, payload["passed_count"])
            self.assertEqual(0, payload["failed_count"])
            self.assertEqual(
                ["command_on_path", "os_home", "project_readiness"],
                [check["id"] for check in payload["checks"]],
            )
            self.assertEqual(["PASS", "PASS", "PASS"], [check["status"] for check in payload["checks"]])

    def test_self_check_returns_one_when_aos_command_is_not_on_path(self):
        with tempfile.TemporaryDirectory() as os_dir, tempfile.TemporaryDirectory() as project_dir:
            self.assertEqual(main(["--os-home", os_dir, "init"], stdout=io.StringIO()), 0)
            project_root = Path(project_dir)
            link_project(project_root, "demo", "Demo Project", "product", "dai", ["codex"])
            self.assertEqual(
                main(
                    ["--os-home", os_dir, "compile", "codex", "--project-root", str(project_root)],
                    stdout=io.StringIO(),
                ),
                0,
            )
            stdout = io.StringIO()

            with patch("agentic_os.self_check.shutil.which", return_value=None):
                code = main(
                    ["--os-home", os_dir, "self-check", "--project-root", str(project_root)],
                    stdout=stdout,
                )

            self.assertEqual(1, code)
            self.assertEqual(
                "AOS self-check issues: 2 passed, 1 failed\n",
                stdout.getvalue(),
            )

    def test_onboarding_check_compiles_providers_and_reports_ok(self):
        with tempfile.TemporaryDirectory() as os_dir, tempfile.TemporaryDirectory() as project_dir:
            self.assertEqual(main(["--os-home", os_dir, "init"], stdout=io.StringIO()), 0)
            project_root = Path(project_dir)
            link_project(project_root, "demo", "Demo Project", "product", "dai", ["codex"])
            stdout = io.StringIO()

            with patch("agentic_os.self_check.shutil.which", return_value="/tmp/bin/aos"):
                code = main(
                    ["--os-home", os_dir, "onboarding-check", "--project-root", str(project_root)],
                    stdout=stdout,
                )

            self.assertEqual(0, code)
            self.assertTrue((project_root / "AGENTS.md").is_file())
            self.assertEqual(
                "AOS onboarding-check ok: 4 passed, 0 failed\n",
                stdout.getvalue(),
            )

    def test_onboarding_check_outputs_json(self):
        with tempfile.TemporaryDirectory() as os_dir, tempfile.TemporaryDirectory() as project_dir:
            self.assertEqual(main(["--os-home", os_dir, "init"], stdout=io.StringIO()), 0)
            project_root = Path(project_dir)
            link_project(project_root, "demo", "Demo Project", "product", "dai", ["codex"])
            stdout = io.StringIO()

            with patch("agentic_os.self_check.shutil.which", return_value="/tmp/bin/aos"):
                code = main(
                    ["--os-home", os_dir, "onboarding-check", "--project-root", str(project_root), "--json"],
                    stdout=stdout,
                )

            payload = json.loads(stdout.getvalue())
            self.assertEqual(0, code)
            self.assertTrue(payload["ok"])
            self.assertEqual(4, payload["passed_count"])
            self.assertEqual(0, payload["failed_count"])
            self.assertEqual(
                ["compile_providers", "self_check", "readiness", "private_scan"],
                [step["id"] for step in payload["steps"]],
            )
            self.assertEqual(["PASS", "PASS", "PASS", "PASS"], [step["status"] for step in payload["steps"]])

    def test_onboarding_check_recompiles_stale_provider_outputs(self):
        with tempfile.TemporaryDirectory() as os_dir, tempfile.TemporaryDirectory() as project_dir:
            self.assertEqual(main(["--os-home", os_dir, "init"], stdout=io.StringIO()), 0)
            project_root = Path(project_dir)
            link_project(project_root, "demo", "Demo Project", "product", "dai", ["codex"])
            self.assertEqual(
                main(
                    ["--os-home", os_dir, "compile", "codex", "--project-root", str(project_root)],
                    stdout=io.StringIO(),
                ),
                0,
            )
            (Path(os_dir) / "core/identity/user.md").write_text(
                "# User Identity\nUpdated project context.\n",
                encoding="utf-8",
            )
            stdout = io.StringIO()

            with patch("agentic_os.self_check.shutil.which", return_value="/tmp/bin/aos"):
                code = main(
                    ["--os-home", os_dir, "onboarding-check", "--project-root", str(project_root), "--json"],
                    stdout=stdout,
                )

            payload = json.loads(stdout.getvalue())
            self.assertEqual(0, code)
            self.assertTrue(payload["ok"])
            self.assertIn("Updated project context.", (project_root / "AGENTS.md").read_text(encoding="utf-8"))

    def test_onboarding_check_returns_one_when_self_check_fails(self):
        with tempfile.TemporaryDirectory() as os_dir, tempfile.TemporaryDirectory() as project_dir:
            self.assertEqual(main(["--os-home", os_dir, "init"], stdout=io.StringIO()), 0)
            project_root = Path(project_dir)
            link_project(project_root, "demo", "Demo Project", "product", "dai", ["codex"])
            stdout = io.StringIO()

            with patch("agentic_os.self_check.shutil.which", return_value=None):
                code = main(
                    ["--os-home", os_dir, "onboarding-check", "--project-root", str(project_root)],
                    stdout=stdout,
                )

            self.assertEqual(1, code)
            self.assertTrue((project_root / "AGENTS.md").is_file())
            self.assertEqual(
                "AOS onboarding-check issues: 3 passed, 1 failed\n",
                stdout.getvalue(),
            )

    def test_memory_add_session_accepts_tags_decisions_and_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.assertEqual(main(["--os-home", temp_dir, "init"], stdout=io.StringIO()), 0)
            stdout = io.StringIO()

            code = main(
                [
                    "--os-home",
                    temp_dir,
                    "memory",
                    "add",
                    "session",
                    "--project-id",
                    "demo",
                    "--title",
                    "Capture Session Metadata",
                    "--summary",
                    "Captured richer session context.",
                    "--tag",
                    "hardening",
                    "--decision",
                    "Store session metadata as front matter",
                    "--artifact",
                    "agentic-os/src/agentic_os/memory.py",
                    "--timestamp",
                    "2026-05-10 09:30",
                ],
                stdout=stdout,
            )

            self.assertEqual(0, code)
            self.assertIn("Recorded session memory", stdout.getvalue())
            session_path = Path(temp_dir) / "memory/sessions/2026-05-10-0930-capture-session-metadata.md"
            content = session_path.read_text(encoding="utf-8")
            self.assertIn("- \"hardening\"", content)
            self.assertIn("- Store session metadata as front matter", content)
            self.assertIn("- agentic-os/src/agentic_os/memory.py", content)

    def test_memory_add_decision_writes_decision_and_project_state(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.assertEqual(main(["--os-home", temp_dir, "init"], stdout=io.StringIO()), 0)
            stdout = io.StringIO()
            rationale = "Preserve rationale format:\n\n- Keep bullets.\n  - Keep indentation."

            code = main(
                [
                    "--os-home",
                    temp_dir,
                    "memory",
                    "add",
                    "decision",
                    "--project-id",
                    "demo",
                    "--title",
                    "Choose Security First",
                    "--rationale",
                    rationale,
                    "--timestamp",
                    "2026-05-10 09:45",
                ],
                stdout=stdout,
            )

            self.assertEqual(0, code)
            self.assertIn("Recorded decision memory", stdout.getvalue())
            decision_path = Path(temp_dir) / "memory/decisions/2026-05-10-0945-choose-security-first.md"
            self.assertTrue(decision_path.is_file())
            self.assertIn(f"## Rationale\n\n{rationale}", decision_path.read_text(encoding="utf-8"))
            project_state = Path(temp_dir) / "memory/project-state/demo.md"
            self.assertTrue(project_state.is_file())
            self.assertIn("Choose Security First", project_state.read_text(encoding="utf-8"))

    def test_memory_list_prints_entries(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.assertEqual(main(["--os-home", temp_dir, "init"], stdout=io.StringIO()), 0)
            self.assertEqual(
                main(
                    [
                        "--os-home",
                        temp_dir,
                        "memory",
                        "add",
                        "session",
                        "--project-id",
                        "demo",
                        "--title",
                        "Listable Session",
                        "--summary",
                        "Captured listable memory.",
                        "--timestamp",
                        "2026-05-10 09:30",
                    ],
                    stdout=io.StringIO(),
                ),
                0,
            )
            stdout = io.StringIO()

            code = main(["--os-home", temp_dir, "memory", "list"], stdout=stdout)

            self.assertEqual(0, code)
            self.assertIn("2026-05-10 09:30\tsession\tdemo\tListable Session\t", stdout.getvalue())

    def test_memory_list_escapes_control_characters_in_fields(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.assertEqual(main(["--os-home", temp_dir, "init"], stdout=io.StringIO()), 0)
            memory_path = Path(temp_dir) / "memory/sessions/manual.md"
            memory_path.write_text(
                "\n".join(
                    [
                        "---",
                        'type: "session"',
                        'project_id: "demo"',
                        'title: "Title\\tWith\\nBreak"',
                        'timestamp: "2026-05-10 09:30"',
                        "---",
                        "",
                        "Manual content.",
                    ]
                ),
                encoding="utf-8",
            )
            stdout = io.StringIO()

            code = main(["--os-home", temp_dir, "memory", "list"], stdout=stdout)

            self.assertEqual(0, code)
            lines = stdout.getvalue().splitlines()
            self.assertEqual(1, len(lines))
            fields = lines[0].split("\t")
            self.assertEqual(5, len(fields))
            self.assertEqual("Title\\tWith\\nBreak", fields[3])

    def test_memory_list_rejects_negative_limit(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.assertEqual(main(["--os-home", temp_dir, "init"], stdout=io.StringIO()), 0)
            stdout = io.StringIO()
            stderr = io.StringIO()

            code = main(
                ["--os-home", temp_dir, "memory", "list", "--limit", "-1"],
                stdout=stdout,
                stderr=stderr,
            )

            self.assertEqual(1, code)
            self.assertEqual("", stdout.getvalue())
            self.assertIn("limit must be non-negative", stderr.getvalue())

    def test_memory_search_prints_title_and_snippet(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.assertEqual(main(["--os-home", temp_dir, "init"], stdout=io.StringIO()), 0)
            self.assertEqual(
                main(
                    [
                        "--os-home",
                        temp_dir,
                        "memory",
                        "add",
                        "session",
                        "--project-id",
                        "demo",
                        "--title",
                        "Searchable Session",
                        "--summary",
                        "Needle appears in CLI output.",
                        "--timestamp",
                        "2026-05-10 09:30",
                    ],
                    stdout=io.StringIO(),
                ),
                0,
            )
            stdout = io.StringIO()

            code = main(["--os-home", temp_dir, "memory", "search", "needle"], stdout=stdout)

            self.assertEqual(0, code)
            output = stdout.getvalue()
            self.assertIn("Searchable Session", output)
            self.assertIn("Needle appears in CLI output.", output)

    def test_memory_search_escapes_control_characters_in_fields(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.assertEqual(main(["--os-home", temp_dir, "init"], stdout=io.StringIO()), 0)
            memory_path = Path(temp_dir) / "memory/sessions/manual.md"
            memory_path.write_text(
                "\n".join(
                    [
                        "---",
                        'type: "session"',
                        'project_id: "demo"',
                        'title: "Title\\tWith\\nBreak"',
                        'timestamp: "2026-05-10 09:30"',
                        "---",
                        "",
                        "Needle\tappears in this line.",
                    ]
                ),
                encoding="utf-8",
            )
            stdout = io.StringIO()

            code = main(["--os-home", temp_dir, "memory", "search", "needle"], stdout=stdout)

            self.assertEqual(0, code)
            lines = stdout.getvalue().splitlines()
            self.assertEqual(1, len(lines))
            fields = lines[0].split("\t")
            self.assertEqual(6, len(fields))
            self.assertEqual("Title\\tWith\\nBreak", fields[3])
            self.assertEqual("Needle\\tappears in this line.", fields[5])
