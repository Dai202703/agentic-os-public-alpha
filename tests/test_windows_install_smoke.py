import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch


class WindowsInstallSmokeTests(unittest.TestCase):
    def setUp(self):
        self.repo_root = Path(__file__).resolve().parents[1]
        script_path = self.repo_root / "scripts/windows_install_smoke.py"
        spec = importlib.util.spec_from_file_location("windows_install_smoke", script_path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Could not load {script_path}")
        self.module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = self.module
        spec.loader.exec_module(self.module)

    def test_smoke_installs_verifies_versions_and_rolls_back(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            repo_root = temp_path / "repo"
            install_dir = temp_path / "bin"
            (repo_root / "scripts").mkdir(parents=True)
            (repo_root / "scripts/install.ps1").write_text("[CmdletBinding()]\n", encoding="utf-8")
            commands: list[list[str]] = []

            def fake_run(command, **kwargs):
                command_text = [str(part) for part in command]
                commands.append(command_text)
                if "install.ps1" in " ".join(command_text) and "-Rollback" not in command_text:
                    install_dir.mkdir(parents=True, exist_ok=True)
                    (install_dir / "aos.cmd").write_text("@echo off\n", encoding="utf-8")
                    (install_dir / "aos.ps1").write_text("exit 0\n", encoding="utf-8")
                    (install_dir / ".aos-install-state.json").write_text("{}\n", encoding="utf-8")
                if "-Rollback" in command_text:
                    for relative in ("aos.cmd", "aos.ps1", ".aos-install-state.json"):
                        path = install_dir / relative
                        if path.exists():
                            path.unlink()
                return subprocess.CompletedProcess(command_text, 0, stdout='{"ok": true}\n', stderr="")

            args = SimpleNamespace(
                repo_root=str(repo_root),
                install_dir=str(install_dir),
                python=sys.executable,
                powershell="powershell",
                json=True,
            )

            with patch.object(self.module.subprocess, "run", side_effect=fake_run):
                steps = self.module.run_smoke(args)

        self.assertTrue(all(step.status == "PASS" for step in steps), steps)
        self.assertEqual(
            [
                "install",
                "aos_cmd_exists",
                "aos_ps1_exists",
                "state_exists",
                "aos_cmd_version",
                "aos_ps1_version",
                "rollback",
                "aos_cmd_removed",
                "aos_ps1_removed",
                "state_removed",
            ],
            [step.id for step in steps],
        )
        command_text = "\n".join(" ".join(command) for command in commands)
        self.assertIn("-File", command_text)
        self.assertIn("install.ps1", command_text)
        self.assertIn("aos.cmd version --json", command_text)
        self.assertIn("aos.ps1 version --json", command_text)
        self.assertIn("-Rollback", command_text)


if __name__ == "__main__":
    unittest.main()
