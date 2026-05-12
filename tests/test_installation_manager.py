import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class InstallationManagerTests(unittest.TestCase):
    def setUp(self):
        self.repo_root = Path(__file__).resolve().parents[1]
        self.manager = self.repo_root / "scripts/manage_global_aos.py"
        self.install_script = self.repo_root / "scripts/install.sh"
        self.launcher = self.repo_root / "bin/aos"

    def run_manager(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(self.manager), *args],
            check=False,
            cwd=self.repo_root,
            text=True,
            capture_output=True,
        )

    def test_install_and_rollback_without_previous_command(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            install_dir = Path(temp_dir) / "bin"
            state_file = Path(temp_dir) / "state.json"

            install = self.run_manager(
                "install",
                "--launcher",
                str(self.launcher),
                "--install-dir",
                str(install_dir),
                "--state-file",
                str(state_file),
            )

            self.assertEqual(0, install.returncode, install.stderr)
            active = install_dir / "aos"
            self.assertTrue(active.is_symlink())
            self.assertEqual(self.launcher.resolve(), active.resolve())
            state = json.loads(state_file.read_text(encoding="utf-8"))
            self.assertIsNone(state["backup_path"])

            rollback = self.run_manager(
                "rollback",
                "--install-dir",
                str(install_dir),
                "--state-file",
                str(state_file),
            )

            self.assertEqual(0, rollback.returncode, rollback.stderr)
            self.assertFalse(active.exists())
            self.assertFalse(active.is_symlink())

    def test_update_backs_up_previous_command_and_rollback_restores_it(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            install_dir = temp_path / "bin"
            install_dir.mkdir()
            state_file = temp_path / "state.json"
            previous_launcher = temp_path / "previous-aos"
            previous_launcher.write_text("#!/usr/bin/env sh\nexit 0\n", encoding="utf-8")
            previous_launcher.chmod(0o755)
            active = install_dir / "aos"
            active.symlink_to(previous_launcher)

            update = self.run_manager(
                "update",
                "--launcher",
                str(self.launcher),
                "--install-dir",
                str(install_dir),
                "--state-file",
                str(state_file),
            )

            self.assertEqual(0, update.returncode, update.stderr)
            self.assertTrue(active.is_symlink())
            self.assertEqual(self.launcher.resolve(), active.resolve())
            state = json.loads(state_file.read_text(encoding="utf-8"))
            backup_path = Path(state["backup_path"])
            self.assertTrue(backup_path.is_symlink())
            self.assertEqual(previous_launcher.resolve(), backup_path.resolve())

            rollback = self.run_manager(
                "rollback",
                "--install-dir",
                str(install_dir),
                "--state-file",
                str(state_file),
            )

            self.assertEqual(0, rollback.returncode, rollback.stderr)
            self.assertTrue(active.is_symlink())
            self.assertEqual(previous_launcher.resolve(), active.resolve())

    def test_install_script_installs_launcher_to_env_install_dir(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            install_dir = Path(temp_dir) / "bin"
            env = os.environ.copy()
            env["AOS_INSTALL_DIR"] = str(install_dir)
            env["AOS_INSTALL_SKIP_CHECKS"] = "1"

            install = subprocess.run(
                ["sh", str(self.install_script)],
                check=False,
                cwd=self.repo_root,
                env=env,
                text=True,
                capture_output=True,
            )

            self.assertEqual(0, install.returncode, install.stderr)
            active = install_dir / "aos"
            self.assertTrue(active.is_symlink())
            self.assertEqual(self.launcher.resolve(), active.resolve())
            self.assertIn("AOS version 0.1.11", install.stdout)
            self.assertIn("Release tag: v0.1.11-public-alpha", install.stdout)
            self.assertIn("aos install complete", install.stdout)
