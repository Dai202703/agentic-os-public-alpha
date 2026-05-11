import tempfile
import unittest
from pathlib import Path

from agentic_os.bootstrap import doctor_os, init_os


class BootstrapTests(unittest.TestCase):
    def test_init_creates_required_directories_and_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = init_os(temp_dir)

            self.assertEqual(root, Path(temp_dir).resolve())
            self.assertTrue((root / "core/identity/user.md").is_file())
            self.assertTrue((root / "core/identity/assistant-style.md").is_file())
            self.assertTrue((root / "core/workstyle/principles.md").is_file())
            self.assertTrue((root / "core/business/portfolio.md").is_file())
            self.assertTrue((root / "memory/sessions").is_dir())
            self.assertTrue((root / "providers/codex/AGENTS.template.md").is_file())
            self.assertTrue((root / "providers/claude/CLAUDE.template.md").is_file())

    def test_init_does_not_overwrite_existing_files_without_force(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = init_os(temp_dir)
            user_file = root / "core/identity/user.md"
            user_file.write_text("custom identity\n", encoding="utf-8")

            init_os(temp_dir)

            self.assertEqual(user_file.read_text(encoding="utf-8"), "custom identity\n")

    def test_doctor_reports_ready_after_init(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            init_os(temp_dir)
            report = doctor_os(temp_dir)

            self.assertTrue(report.ok)
            self.assertEqual(report.missing, [])

    def test_init_rejects_symlinked_managed_directory_outside_os_home(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            root = base_path / "os"
            outside_dir = base_path / "outside"
            root.mkdir()
            outside_dir.mkdir()
            try:
                (root / "core").symlink_to(outside_dir, target_is_directory=True)
            except (NotImplementedError, OSError) as error:
                self.skipTest(f"Symlink creation is unsupported: {error}")

            with self.assertRaises(ValueError):
                init_os(root)

            self.assertFalse((outside_dir / "identity/user.md").exists())
