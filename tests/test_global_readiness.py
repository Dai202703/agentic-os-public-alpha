import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


class GlobalReadinessTests(unittest.TestCase):
    def test_repo_launcher_runs_from_outside_repository(self):
        agentic_os_root = Path(__file__).resolve().parents[1]
        launcher = agentic_os_root / "bin/aos"

        with tempfile.TemporaryDirectory() as os_dir, tempfile.TemporaryDirectory() as outside_cwd:
            result = subprocess.run(
                [str(launcher), "--os-home", os_dir, "init"],
                cwd=outside_cwd,
                env=_without_pythonpath(),
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual("", result.stderr)
            self.assertEqual(0, result.returncode)
            self.assertIn("Initialized Agentic OS", result.stdout)
            self.assertTrue((Path(os_dir) / "core/identity/user.md").is_file())

    def test_repo_launcher_resolves_symlink_install_from_outside_repository(self):
        agentic_os_root = Path(__file__).resolve().parents[1]
        launcher = agentic_os_root / "bin/aos"

        with (
            tempfile.TemporaryDirectory() as install_dir,
            tempfile.TemporaryDirectory() as os_dir,
            tempfile.TemporaryDirectory() as outside_cwd,
        ):
            installed_launcher = Path(install_dir) / "aos"
            try:
                installed_launcher.symlink_to(launcher)
            except (NotImplementedError, OSError) as error:
                self.skipTest(f"Symlink creation is unsupported: {error}")

            result = subprocess.run(
                [str(installed_launcher), "--os-home", os_dir, "init"],
                cwd=outside_cwd,
                env=_without_pythonpath(),
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual("", result.stderr)
            self.assertEqual(0, result.returncode)
            self.assertIn("Initialized Agentic OS", result.stdout)
            self.assertTrue((Path(os_dir) / "core/identity/user.md").is_file())

    def test_readiness_smoke_runs_from_outside_repository(self):
        agentic_os_root = Path(__file__).resolve().parents[1]
        launcher = agentic_os_root / "bin/aos"
        smoke = agentic_os_root / "scripts/readiness_smoke.py"

        with tempfile.TemporaryDirectory() as outside_cwd:
            result = subprocess.run(
                [str(smoke), "--launcher", str(launcher), "--json"],
                cwd=outside_cwd,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual("", result.stderr)
            self.assertEqual(0, result.returncode)
            payload = json.loads(result.stdout)
            self.assertTrue(payload["ok"])
            self.assertEqual(["codex", "claude", "gemini", "chatgpt"], payload["providers_compiled"])
            self.assertEqual(4, payload["provider_outputs_verified"])
            self.assertEqual(2, payload["memory_entries_recorded"])
            self.assertNotEqual(str(agentic_os_root), payload["execution_cwd"])


def _without_pythonpath() -> dict[str, str]:
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    return env
