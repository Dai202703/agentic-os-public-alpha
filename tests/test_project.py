import io
import os
import tempfile
import unittest
from pathlib import Path

from agentic_os.cli import main
from agentic_os.project import link_project, read_project_config, validate_project_config


class ProjectLinkingTests(unittest.TestCase):
    def test_link_project_writes_project_config(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir) / "project"
            project_root.mkdir()

            config_path = link_project(
                project_root,
                project_id="petsona",
                name="Petsona MVP",
                project_type="product",
                owner="dai",
                providers=["codex", "claude"],
            )

            self.assertTrue(config_path.is_file())
            content = config_path.read_text(encoding="utf-8")
            self.assertIn('id: "petsona"', content)
            self.assertIn('name: "Petsona MVP"', content)
            self.assertIn('  - "codex"', content)
            self.assertIn("include_recent_sessions: 3", content)
            self.assertIn("include_recent_decisions: 5", content)

    def test_read_project_config_parses_generated_yaml(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir) / "project"
            project_root.mkdir()
            link_project(project_root, "petsona", "Petsona MVP", "product", "dai", ["codex"])

            config = read_project_config(project_root / ".agentic-os/project.yaml")

            self.assertEqual(config["id"], "petsona")
            self.assertEqual(config["name"], "Petsona MVP")
            self.assertEqual(config["providers"], ["codex"])
            self.assertEqual(config["outputs"]["root"], "outputs/petsona")
            self.assertEqual(config["memory"]["include_recent_sessions"], 3)
            self.assertEqual(config["memory"]["include_recent_decisions"], 5)

    def test_link_project_accepts_user_defined_category_ids(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)

            for project_id, name in [
                ("book-draft", "Book Draft"),
                ("case-research", "Case Research"),
                ("student_notes", "Student Notes"),
            ]:
                with self.subTest(project_id=project_id):
                    config_path = link_project(
                        project_root / project_id,
                        project_id,
                        name,
                        "custom",
                        "user",
                        ["codex"],
                    )

                    config = read_project_config(config_path)

                    self.assertEqual(project_id, config["id"])
                    self.assertEqual(name, config["name"])
                    self.assertEqual("custom", config["type"])
                    self.assertEqual(f"outputs/{project_id}", config["outputs"]["root"])

    def test_read_project_config_parses_unquoted_digit_scalars_as_ints(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "project.yaml"
            config_path.write_text(
                """id: "demo"
name: "Demo Project"
priority: 7
memory:
  include_recent_sessions: 1
  quoted_limit: "5"
contexts:
  - core/identity
providers:
  - "codex"
""",
                encoding="utf-8",
            )

            config = read_project_config(config_path)

            self.assertEqual(config["priority"], 7)
            self.assertEqual(config["memory"]["include_recent_sessions"], 1)
            self.assertEqual(config["memory"]["quoted_limit"], "5")

    def test_read_project_config_preserves_inline_scalars_for_known_list_sections(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "project.yaml"
            config_path.write_text(
                """id: "demo"
name: "Demo Project"
contexts: core/identity
providers: codex
""",
                encoding="utf-8",
            )

            config = read_project_config(config_path)

            self.assertEqual("core/identity", config["contexts"])
            self.assertEqual("codex", config["providers"])
            with self.assertRaises(ValueError):
                validate_project_config(config)

    def test_read_project_config_rejects_list_sections_without_dash_items(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "project.yaml"
            config_path.write_text(
                """id: "demo"
name: "Demo Project"
contexts:
  core/identity
providers:
  codex
""",
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                read_project_config(config_path)

    def test_read_project_config_rejects_indentationless_list_items(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "project.yaml"
            config_path.write_text(
                """id: "demo"
name: "Demo Project"
contexts:
- core/identity
providers:
- unknown-ai
""",
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                read_project_config(config_path)

    def test_link_project_rejects_path_unsafe_project_id(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir) / "project"
            project_root.mkdir()

            with self.assertRaises(ValueError):
                link_project(project_root, "../escape", "Escape", "project", "dai", ["codex"])

    def test_link_project_rejects_path_unsafe_provider_id(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir) / "project"
            project_root.mkdir()

            with self.assertRaises(ValueError):
                link_project(project_root, "petsona", "Petsona MVP", "project", "dai", ["../outside"])

    def test_link_project_rejects_unknown_safe_provider_without_writing_config(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir) / "project"
            project_root.mkdir()

            with self.assertRaises(ValueError):
                link_project(
                    project_root,
                    "petsona",
                    "Petsona MVP",
                    "project",
                    "dai",
                    ["unknown-ai"],
                )

            self.assertFalse((project_root / ".agentic-os/project.yaml").exists())

    def test_link_project_rejects_symlinked_config_directory_without_writing_outside(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir) / "project"
            outside = Path(temp_dir) / "outside"
            project_root.mkdir()
            outside.mkdir()
            try:
                (project_root / ".agentic-os").symlink_to(outside, target_is_directory=True)
            except (NotImplementedError, OSError) as error:
                self.skipTest(f"Symlink creation is unsupported: {error}")

            with self.assertRaises(ValueError):
                link_project(
                    project_root,
                    "petsona",
                    "Petsona MVP",
                    "project",
                    "dai",
                    ["codex"],
                )

            self.assertFalse((outside / "project.yaml").exists())

    def test_link_project_rejects_hardlinked_config_file_without_writing_outside(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir) / "project"
            outside_config = Path(temp_dir) / "outside-project.yaml"
            config_path = project_root / ".agentic-os/project.yaml"
            project_root.mkdir()
            config_path.parent.mkdir()
            outside_config.write_text("outside config\n", encoding="utf-8")
            try:
                os.link(outside_config, config_path)
            except (NotImplementedError, OSError) as error:
                self.skipTest(f"Hardlink creation is unsupported: {error}")

            with self.assertRaises(ValueError):
                link_project(
                    project_root,
                    "petsona",
                    "Petsona MVP",
                    "project",
                    "dai",
                    ["codex"],
                )

            self.assertEqual(outside_config.read_text(encoding="utf-8"), "outside config\n")

    def test_link_project_rejects_symlinked_project_root_without_writing_target(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            real_project_root = Path(temp_dir) / "real-project"
            project_root = Path(temp_dir) / "project-link"
            real_project_root.mkdir()
            try:
                project_root.symlink_to(real_project_root, target_is_directory=True)
            except (NotImplementedError, OSError) as error:
                self.skipTest(f"Symlink creation is unsupported: {error}")

            with self.assertRaises(ValueError):
                link_project(
                    project_root,
                    "petsona",
                    "Petsona MVP",
                    "project",
                    "dai",
                    ["codex"],
                )

            self.assertFalse((real_project_root / ".agentic-os/project.yaml").exists())

    def test_link_project_rejects_symlink_component_before_parent_segment_without_writing_target(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            real_project_root = Path(temp_dir) / "real-project"
            project_link = Path(temp_dir) / "project-link"
            real_project_root.mkdir()
            (real_project_root / "nested").mkdir()
            try:
                project_link.symlink_to(real_project_root, target_is_directory=True)
            except (NotImplementedError, OSError) as error:
                self.skipTest(f"Symlink creation is unsupported: {error}")

            with self.assertRaises(ValueError):
                link_project(
                    project_link / "nested" / "..",
                    "petsona",
                    "Petsona MVP",
                    "project",
                    "dai",
                    ["codex"],
                )

            self.assertFalse((real_project_root / ".agentic-os/project.yaml").exists())

    def test_link_project_quotes_and_reads_symbol_scalars(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir) / "project"
            project_root.mkdir()

            config_path = link_project(
                project_root,
                "petsona",
                "Name # With: Symbols",
                "product",
                "dai",
                ["codex"],
            )

            content = config_path.read_text(encoding="utf-8")
            self.assertIn('name: "Name # With: Symbols"', content)

            config = read_project_config(config_path)

            self.assertEqual(config["name"], "Name # With: Symbols")

    def test_link_project_command_uses_default_providers(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir) / "project"
            stdout = io.StringIO()

            status = main(
                [
                    "link-project",
                    "--project-root",
                    str(project_root),
                    "--id",
                    "petsona",
                    "--name",
                    "Petsona MVP",
                ],
                stdout=stdout,
            )

            config = read_project_config(project_root / ".agentic-os/project.yaml")
            self.assertEqual(status, 0)
            self.assertIn("Linked project at", stdout.getvalue())
            self.assertEqual(config["providers"], ["codex", "claude"])

    def test_link_project_command_uses_repeated_providers(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir) / "project"
            stdout = io.StringIO()

            status = main(
                [
                    "link-project",
                    "--project-root",
                    str(project_root),
                    "--id",
                    "petsona",
                    "--name",
                    "Petsona MVP",
                    "--provider",
                    "codex",
                    "--provider",
                    "gemini",
                ],
                stdout=stdout,
            )

            config = read_project_config(project_root / ".agentic-os/project.yaml")
            self.assertEqual(status, 0)
            self.assertEqual(config["providers"], ["codex", "gemini"])

    def test_link_project_quotes_and_reads_provider_list_items(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir) / "project"
            project_root.mkdir()

            config_path = link_project(
                project_root,
                "petsona",
                "Petsona MVP",
                "product",
                "dai",
                ["codex", "gemini"],
            )

            content = config_path.read_text(encoding="utf-8")
            self.assertIn('  - "codex"', content)
            self.assertIn('  - "gemini"', content)

            config = read_project_config(config_path)

            self.assertEqual(config["providers"], ["codex", "gemini"])

    def test_link_project_command_returns_error_for_path_unsafe_project_id(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir) / "project"
            stderr = io.StringIO()

            status = main(
                [
                    "link-project",
                    "--project-root",
                    str(project_root),
                    "--id",
                    "../escape",
                    "--name",
                    "Escape",
                ],
                stderr=stderr,
            )

            self.assertEqual(status, 1)
            self.assertIn("Error:", stderr.getvalue())

    def test_link_project_command_returns_error_for_path_unsafe_provider_id(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir) / "project"
            stderr = io.StringIO()

            status = main(
                [
                    "link-project",
                    "--project-root",
                    str(project_root),
                    "--id",
                    "petsona",
                    "--name",
                    "Petsona MVP",
                    "--provider",
                    "../outside",
                ],
                stderr=stderr,
            )

            self.assertEqual(status, 1)
            self.assertIn("Error:", stderr.getvalue())

    def test_validate_project_config_rejects_unknown_provider(self):
        from agentic_os.project import validate_project_config

        config = {
            "id": "demo",
            "name": "Demo Project",
            "contexts": ["core/identity"],
            "providers": ["codex", "unknown-ai"],
            "outputs": {"root": "outputs/demo"},
        }

        with self.assertRaises(ValueError):
            validate_project_config(config)

    def test_validate_project_config_rejects_unsafe_output_root(self):
        from agentic_os.project import validate_project_config

        config = {
            "id": "demo",
            "name": "Demo Project",
            "contexts": ["core/identity"],
            "providers": ["codex"],
            "outputs": {"root": "../outside"},
        }

        with self.assertRaises(ValueError):
            validate_project_config(config)

    def test_validate_project_config_rejects_non_integer_recent_memory_limits(self):
        from agentic_os.project import validate_project_config

        for key, value in [
            ("include_recent_sessions", "3"),
            ("include_recent_sessions", "abc"),
            ("include_recent_decisions", "3"),
            ("include_recent_decisions", "abc"),
        ]:
            with self.subTest(key=key, value=value):
                config = {
                    "id": "demo",
                    "name": "Demo Project",
                    "contexts": ["core/identity"],
                    "providers": ["codex"],
                    "memory": {key: value},
                }

                with self.assertRaises(ValueError):
                    validate_project_config(config)

    def test_validate_project_config_rejects_negative_recent_memory_limits(self):
        from agentic_os.project import validate_project_config

        for key in ["include_recent_sessions", "include_recent_decisions"]:
            with self.subTest(key=key):
                config = {
                    "id": "demo",
                    "name": "Demo Project",
                    "contexts": ["core/identity"],
                    "providers": ["codex"],
                    "memory": {key: -1},
                }

                with self.assertRaises(ValueError):
                    validate_project_config(config)
