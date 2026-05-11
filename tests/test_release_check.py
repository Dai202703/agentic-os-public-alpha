import io
import json
from types import SimpleNamespace
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agentic_os.cli import main
from agentic_os.release_check import release_check


class ReleaseCheckTests(unittest.TestCase):
    def test_release_check_runs_core_gates(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = self.create_release_repo(Path(temp_dir))
            calls: list[list[str]] = []

            def fake_run(command, **kwargs):
                calls.append([str(part) for part in command])
                return subprocess.CompletedProcess(command, 0, stdout="ok\n", stderr="")

            with patch("agentic_os.release_check.subprocess.run", side_effect=fake_run):
                report = release_check(repo_root)

            self.assertTrue(report.ok)
            self.assertEqual(
                [
                    "version_consistency",
                    "unit_tests",
                    "readiness_smoke",
                    "distribution_check",
                    "install_manager_dry_run",
                ],
                [step.id for step in report.steps],
            )
            command_text = "\n".join(" ".join(command) for command in calls)
            self.assertIn("unittest discover -s tests -v", command_text)
            self.assertIn("readiness_smoke.py", command_text)
            self.assertIn("manage_global_aos.py install", command_text)
            self.assertIn("manage_global_aos.py update", command_text)
            self.assertIn("manage_global_aos.py rollback", command_text)

    def test_release_check_can_include_upgrade_smoke_when_requested(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = self.create_release_repo(Path(temp_dir))

            def fake_run(command, **kwargs):
                return subprocess.CompletedProcess(command, 0, stdout="ok\n", stderr="")

            fake_report = SimpleNamespace(
                ok=True,
                failed=[],
                previous_version={"release_tag": "v0.1.3-public-alpha"},
                current_version={"release_tag": "v0.1.4-public-alpha"},
            )

            with patch("agentic_os.release_check.subprocess.run", side_effect=fake_run):
                with patch("agentic_os.release_check.release_upgrade_smoke", return_value=fake_report) as fake_smoke:
                    report = release_check(
                        repo_root,
                        upgrade_smoke=True,
                        from_ref="v0.1.3-public-alpha",
                        to_ref="HEAD",
                    )

            self.assertTrue(report.ok)
            self.assertEqual("release_upgrade_smoke", report.steps[-1].id)
            self.assertIn("v0.1.3-public-alpha", report.steps[-1].message)
            self.assertIn("v0.1.4-public-alpha", report.steps[-1].message)
            fake_smoke.assert_called_once_with(
                repo_root.resolve(),
                from_ref="v0.1.3-public-alpha",
                to_ref="HEAD",
            )

    def test_release_check_fails_when_distribution_check_finds_private_output(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = self.create_release_repo(Path(temp_dir))
            (repo_root / "AGENTS.md").write_text("# Generated provider output\n", encoding="utf-8")

            with patch("agentic_os.release_check.subprocess.run") as fake_run:
                fake_run.return_value = subprocess.CompletedProcess([], 0, stdout="ok\n", stderr="")
                report = release_check(repo_root)

            self.assertFalse(report.ok)
            failed = [step for step in report.steps if step.status == "FAIL"]
            self.assertEqual(["distribution_check"], [step.id for step in failed])
            self.assertIn("1 findings", failed[0].message)

    def test_release_check_fails_when_changelog_version_drifts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = self.create_release_repo(Path(temp_dir))
            (repo_root / "CHANGELOG.md").write_text(
                "# Changelog\n\n## v9.9.9-public-alpha\n\n- Drifted release.\n",
                encoding="utf-8",
            )

            with patch("agentic_os.release_check.subprocess.run") as fake_run:
                fake_run.return_value = subprocess.CompletedProcess([], 0, stdout="ok\n", stderr="")
                report = release_check(repo_root)

            self.assertFalse(report.ok)
            failed = [step for step in report.steps if step.status == "FAIL"]
            self.assertEqual(["version_consistency"], [step.id for step in failed])
            self.assertIn("expected v0.1.4-public-alpha", failed[0].message)

    def test_release_check_cli_outputs_json(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = self.create_release_repo(Path(temp_dir))
            stdout = io.StringIO()

            with patch("agentic_os.release_check.subprocess.run") as fake_run:
                fake_run.return_value = subprocess.CompletedProcess([], 0, stdout="ok\n", stderr="")
                code = main(["release-check", "--repo-root", str(repo_root), "--json"], stdout=stdout)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(0, code)
            self.assertTrue(payload["ok"])
            self.assertEqual(5, payload["passed_count"])
            self.assertEqual(0, payload["failed_count"])
            self.assertEqual(
                [
                    "version_consistency",
                    "unit_tests",
                    "readiness_smoke",
                    "distribution_check",
                    "install_manager_dry_run",
                ],
                [step["id"] for step in payload["steps"]],
            )

    def create_release_repo(self, repo_root: Path) -> Path:
        (repo_root / "src/agentic_os").mkdir(parents=True)
        (repo_root / "src/agentic_os/version.py").write_text(
            'VERSION = "0.1.4"\nRELEASE_CHANNEL = "public-alpha"\n',
            encoding="utf-8",
        )
        (repo_root / "pyproject.toml").write_text(
            '[project]\nname = "agentic-os"\nversion = "0.1.4"\n',
            encoding="utf-8",
        )
        (repo_root / "CHANGELOG.md").write_text(
            "# Changelog\n\n## v0.1.4-public-alpha\n\n- Release upgrade smoke.\n",
            encoding="utf-8",
        )
        (repo_root / "bin").mkdir()
        launcher = repo_root / "bin/aos"
        launcher.write_text("#!/usr/bin/env sh\nexit 0\n", encoding="utf-8")
        launcher.chmod(0o755)
        (repo_root / "scripts").mkdir()
        (repo_root / "scripts/readiness_smoke.py").write_text("#!/usr/bin/env python3\n", encoding="utf-8")
        (repo_root / "scripts/manage_global_aos.py").write_text("#!/usr/bin/env python3\n", encoding="utf-8")
        (repo_root / "tests").mkdir()
        (repo_root / "tests/test_placeholder.py").write_text("import unittest\n", encoding="utf-8")
        (repo_root / "README.md").write_text("Shareable package\n", encoding="utf-8")
        return repo_root


if __name__ == "__main__":
    unittest.main()
