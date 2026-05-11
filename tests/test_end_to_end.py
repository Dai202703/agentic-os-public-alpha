import io
import tempfile
import unittest
from pathlib import Path

from agentic_os.cli import main


class EndToEndTests(unittest.TestCase):
    def test_local_mvp_flow(self):
        with tempfile.TemporaryDirectory() as os_dir, tempfile.TemporaryDirectory() as project_dir:
            project_root = Path(project_dir)

            self.assertEqual(main(["--os-home", os_dir, "init"], stdout=io.StringIO()), 0)
            self.assertEqual(main(["--os-home", os_dir, "doctor"], stdout=io.StringIO()), 0)
            self.assertEqual(
                main(
                    [
                        "--os-home",
                        os_dir,
                        "link-project",
                        "--project-root",
                        str(project_root),
                        "--id",
                        "demo",
                        "--name",
                        "Demo Project",
                        "--provider",
                        "codex",
                    ],
                    stdout=io.StringIO(),
                ),
                0,
            )
            self.assertEqual(
                main(["--os-home", os_dir, "compile", "codex", "--project-root", str(project_root)], stdout=io.StringIO()),
                0,
            )
            self.assertEqual(
                main(
                    [
                        "--os-home",
                        os_dir,
                        "memory",
                        "add",
                        "session",
                        "--project-id",
                        "demo",
                        "--title",
                        "Smoke Test",
                        "--summary",
                        "Verified local MVP flow.",
                    ],
                    stdout=io.StringIO(),
                ),
                0,
            )
            self.assertEqual(
                main(["--os-home", os_dir, "skill", "create", "research-summary", "--name", "Research Summary"], stdout=io.StringIO()),
                0,
            )
            self.assertEqual(
                main(["--os-home", os_dir, "workflow", "create", "idea-to-spec", "--name", "Idea to Spec"], stdout=io.StringIO()),
                0,
            )
            self.assertEqual(
                main(
                    [
                        "--os-home",
                        os_dir,
                        "memory",
                        "add",
                        "decision",
                        "--project-id",
                        "demo",
                        "--title",
                        "Use AOS",
                        "--rationale",
                        "Provider context should be generated from one source.",
                        "--timestamp",
                        "2026-05-10 09:45",
                    ],
                    stdout=io.StringIO(),
                ),
                0,
            )
            self.assertEqual(
                main(["--os-home", os_dir, "memory", "list", "--project-id", "demo"], stdout=io.StringIO()),
                0,
            )
            self.assertEqual(
                main(
                    [
                        "--os-home",
                        os_dir,
                        "memory",
                        "search",
                        "Provider context",
                        "--project-id",
                        "demo",
                    ],
                    stdout=io.StringIO(),
                ),
                0,
            )
            self.assertEqual(
                main(["--os-home", os_dir, "doctor", "--project-root", str(project_root)], stdout=io.StringIO()),
                0,
            )

            self.assertTrue((project_root / "AGENTS.md").is_file())
            self.assertTrue((Path(os_dir) / "memory/project-state/demo.md").is_file())
            self.assertTrue((Path(os_dir) / "skills/research-summary/SKILL.md").is_file())
            self.assertTrue((Path(os_dir) / "workflows/idea-to-spec/workflow.yaml").is_file())
