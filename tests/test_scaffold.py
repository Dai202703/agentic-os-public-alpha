import io
import shutil
import tempfile
import unittest
from pathlib import Path

from agentic_os.bootstrap import init_os
from agentic_os.cli import main
from agentic_os.scaffold import create_skill, create_workflow


class ScaffoldTests(unittest.TestCase):
    def test_create_skill_writes_standard_skill_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os_home = init_os(temp_dir)

            skill_dir = create_skill(os_home, "research-summary", "Research Summary")

            self.assertTrue((skill_dir / "SKILL.md").is_file())
            self.assertTrue((skill_dir / "examples").is_dir())
            self.assertTrue((skill_dir / "references").is_dir())
            self.assertTrue((skill_dir / "learnings.md").is_file())
            self.assertIn("Research Summary", (skill_dir / "SKILL.md").read_text(encoding="utf-8"))

    def test_create_workflow_writes_standard_workflow_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os_home = init_os(temp_dir)

            workflow_dir = create_workflow(os_home, "idea-to-spec", "Idea to Spec")

            self.assertTrue((workflow_dir / "workflow.yaml").is_file())
            self.assertTrue((workflow_dir / "README.md").is_file())
            self.assertTrue((workflow_dir / "prompts").is_dir())
            self.assertTrue((workflow_dir / "examples").is_dir())
            self.assertIn("Idea to Spec", (workflow_dir / "README.md").read_text(encoding="utf-8"))

    def test_create_skill_rejects_path_traversal_id(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os_home = init_os(temp_dir)

            with self.assertRaises(ValueError):
                create_skill(os_home, "../../outside-skill", "Bad")

    def test_create_workflow_rejects_path_traversal_id(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os_home = init_os(temp_dir)

            with self.assertRaises(ValueError):
                create_workflow(os_home, "../../outside-workflow", "Bad")

    def test_create_skill_rejects_absolute_id(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os_home = init_os(temp_dir)

            with self.assertRaises(ValueError):
                create_skill(os_home, "/tmp/outside-skill", "Bad")

    def test_create_skill_rejects_symlinked_skills_directory_outside_os_home(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os_home = init_os(temp_dir)
            outside_dir = Path(temp_dir) / "outside-skills"
            outside_dir.mkdir()
            shutil.rmtree(os_home / "skills")
            try:
                (os_home / "skills").symlink_to(outside_dir, target_is_directory=True)
            except (NotImplementedError, OSError) as error:
                self.skipTest(f"Symlink creation is unsupported: {error}")

            with self.assertRaises(ValueError):
                create_skill(os_home, "research-summary", "Research Summary")

            self.assertFalse((outside_dir / "research-summary/SKILL.md").exists())

    def test_create_workflow_rejects_absolute_id(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os_home = init_os(temp_dir)

            with self.assertRaises(ValueError):
                create_workflow(os_home, "/tmp/outside-workflow", "Bad")

    def test_create_workflow_rejects_symlinked_workflows_directory_outside_os_home(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os_home = init_os(temp_dir)
            outside_dir = Path(temp_dir) / "outside-workflows"
            outside_dir.mkdir()
            shutil.rmtree(os_home / "workflows")
            try:
                (os_home / "workflows").symlink_to(outside_dir, target_is_directory=True)
            except (NotImplementedError, OSError) as error:
                self.skipTest(f"Symlink creation is unsupported: {error}")

            with self.assertRaises(ValueError):
                create_workflow(os_home, "idea-to-spec", "Idea to Spec")

            self.assertFalse((outside_dir / "idea-to-spec/workflow.yaml").exists())

    def test_skill_create_command_reports_invalid_id(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os_home = init_os(temp_dir)
            stderr = io.StringIO()

            exit_code = main(
                ["--os-home", str(os_home), "skill", "create", "../../outside", "--name", "Bad"],
                stdout=io.StringIO(),
                stderr=stderr,
            )

            self.assertEqual(1, exit_code)
            self.assertIn("Error:", stderr.getvalue())

    def test_workflow_create_command_reports_invalid_id(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os_home = init_os(temp_dir)
            stderr = io.StringIO()

            exit_code = main(
                ["--os-home", str(os_home), "workflow", "create", "../../outside", "--name", "Bad"],
                stdout=io.StringIO(),
                stderr=stderr,
            )

            self.assertEqual(1, exit_code)
            self.assertIn("Error:", stderr.getvalue())

    def test_skill_create_command_writes_standard_skill_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os_home = init_os(temp_dir)

            exit_code = main(
                [
                    "--os-home",
                    str(os_home),
                    "skill",
                    "create",
                    "research-summary",
                    "--name",
                    "Research Summary",
                ],
                stdout=io.StringIO(),
                stderr=io.StringIO(),
            )

            skill_dir = os_home / "skills" / "research-summary"
            self.assertEqual(0, exit_code)
            self.assertTrue((skill_dir / "SKILL.md").is_file())
            self.assertTrue((skill_dir / "examples").is_dir())
            self.assertTrue((skill_dir / "references").is_dir())
            self.assertTrue((skill_dir / "learnings.md").is_file())

    def test_workflow_create_command_writes_standard_workflow_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os_home = init_os(temp_dir)

            exit_code = main(
                [
                    "--os-home",
                    str(os_home),
                    "workflow",
                    "create",
                    "idea-to-spec",
                    "--name",
                    "Idea to Spec",
                ],
                stdout=io.StringIO(),
                stderr=io.StringIO(),
            )

            workflow_dir = os_home / "workflows" / "idea-to-spec"
            self.assertEqual(0, exit_code)
            self.assertTrue((workflow_dir / "workflow.yaml").is_file())
            self.assertTrue((workflow_dir / "README.md").is_file())
            self.assertTrue((workflow_dir / "prompts").is_dir())
            self.assertTrue((workflow_dir / "examples").is_dir())

    def test_create_skill_does_not_overwrite_existing_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os_home = init_os(temp_dir)
            skill_dir = create_skill(os_home, "research-summary", "Research Summary")
            skill_file = skill_dir / "SKILL.md"
            learnings_file = skill_dir / "learnings.md"
            skill_file.write_text("custom skill", encoding="utf-8")
            learnings_file.write_text("custom learnings", encoding="utf-8")

            create_skill(os_home, "research-summary", "Research Summary")

            self.assertEqual("custom skill", skill_file.read_text(encoding="utf-8"))
            self.assertEqual("custom learnings", learnings_file.read_text(encoding="utf-8"))

    def test_create_workflow_does_not_overwrite_existing_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os_home = init_os(temp_dir)
            workflow_dir = create_workflow(os_home, "idea-to-spec", "Idea to Spec")
            workflow_file = workflow_dir / "workflow.yaml"
            readme_file = workflow_dir / "README.md"
            workflow_file.write_text("custom workflow", encoding="utf-8")
            readme_file.write_text("custom readme", encoding="utf-8")

            create_workflow(os_home, "idea-to-spec", "Idea to Spec")

            self.assertEqual("custom workflow", workflow_file.read_text(encoding="utf-8"))
            self.assertEqual("custom readme", readme_file.read_text(encoding="utf-8"))

    def test_workflow_yaml_quotes_yaml_like_name(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os_home = init_os(temp_dir)

            workflow_dir = create_workflow(os_home, "idea-to-spec", "Idea # To: Spec")

            workflow_yaml = (workflow_dir / "workflow.yaml").read_text(encoding="utf-8")
            self.assertIn('name: "Idea # To: Spec"', workflow_yaml)
            self.assertNotIn("name: Idea # To: Spec", workflow_yaml)
