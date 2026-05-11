import io
import tempfile
import unittest
from pathlib import Path

from agentic_os.bootstrap import init_os
from agentic_os.cli import main
from agentic_os.memory import add_session_memory
from agentic_os.memory_index import search_memory
from agentic_os.project import link_project


class ReliabilityTests(unittest.TestCase):
    def test_search_handles_many_memory_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os_home = init_os(temp_dir)
            for index in range(120):
                add_session_memory(
                    os_home,
                    project_id="demo",
                    title=f"Session {index}",
                    summary=f"Summary number {index}",
                    timestamp=f"2026-05-10 {index // 60:02d}:{index % 60:02d}",
                )

            results = search_memory(os_home, "Summary number 119", project_id="demo")

            self.assertEqual(1, len(results))
            self.assertEqual("Session 119", results[0].title)

    def test_compile_reports_malformed_project_config(self):
        with tempfile.TemporaryDirectory() as os_dir, tempfile.TemporaryDirectory() as project_dir:
            self.assertEqual(main(["--os-home", os_dir, "init"], stdout=io.StringIO()), 0)
            project_root = Path(project_dir)
            config_dir = project_root / ".agentic-os"
            config_dir.mkdir()
            (config_dir / "project.yaml").write_text(
                """id: "../bad"
name: "Bad Project"
contexts:
  - core/identity
providers:
  - "codex"
""",
                encoding="utf-8",
            )

            code = main(
                ["--os-home", os_dir, "compile", "codex", "--project-root", str(project_root)],
                stdout=io.StringIO(),
                stderr=io.StringIO(),
            )

            self.assertEqual(1, code)

    def test_project_doctor_reports_missing_generated_files_without_failing(self):
        with tempfile.TemporaryDirectory() as os_dir, tempfile.TemporaryDirectory() as project_dir:
            self.assertEqual(main(["--os-home", os_dir, "init"], stdout=io.StringIO()), 0)
            project_root = Path(project_dir)
            link_project(project_root, "demo", "Demo Project", "product", "dai", ["codex"])
            stdout = io.StringIO()

            code = main(
                ["--os-home", os_dir, "doctor", "--project-root", str(project_root)],
                stdout=stdout,
            )

            self.assertEqual(0, code)
            self.assertIn("GENERATED_FILE_MISSING", stdout.getvalue())
