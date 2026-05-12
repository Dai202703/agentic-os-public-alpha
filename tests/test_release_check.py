import io
import hashlib
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
                    "release_manifest",
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

    def test_release_check_fails_when_release_manifest_is_stale(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = self.create_release_repo(Path(temp_dir))
            (repo_root / "README.md").write_text("Changed after manifest\n", encoding="utf-8")

            with patch("agentic_os.release_check.subprocess.run") as fake_run:
                fake_run.return_value = subprocess.CompletedProcess([], 0, stdout="ok\n", stderr="")
                report = release_check(repo_root)

            self.assertFalse(report.ok)
            failed = [step for step in report.steps if step.status == "FAIL"]
            self.assertEqual(["release_manifest"], [step.id for step in failed])
            self.assertIn("1 findings", failed[0].message)

    def test_release_check_can_skip_release_manifest_for_standalone_ci(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = self.create_release_repo(Path(temp_dir))
            (repo_root / "public-release-manifest.json").unlink()

            with patch("agentic_os.release_check.subprocess.run") as fake_run:
                fake_run.return_value = subprocess.CompletedProcess([], 0, stdout="ok\n", stderr="")
                report = release_check(repo_root, release_manifest_gate=False)

            self.assertTrue(report.ok)
            self.assertNotIn("release_manifest", [step.id for step in report.steps])

    def test_release_check_can_include_upgrade_smoke_when_requested(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = self.create_release_repo(Path(temp_dir))

            def fake_run(command, **kwargs):
                return subprocess.CompletedProcess(command, 0, stdout="ok\n", stderr="")

            fake_report = SimpleNamespace(
                ok=True,
                failed=[],
                previous_version={"release_tag": "v0.1.4-public-alpha"},
                current_version={"release_tag": "v0.1.5-public-alpha"},
            )

            with patch("agentic_os.release_check.subprocess.run", side_effect=fake_run):
                with patch("agentic_os.release_check.release_upgrade_smoke", return_value=fake_report) as fake_smoke:
                    report = release_check(
                        repo_root,
                        upgrade_smoke=True,
                        from_ref="v0.1.4-public-alpha",
                        to_ref="HEAD",
                    )

            self.assertTrue(report.ok)
            self.assertEqual("release_upgrade_smoke", report.steps[-1].id)
            self.assertIn("v0.1.4-public-alpha", report.steps[-1].message)
            self.assertIn("v0.1.5-public-alpha", report.steps[-1].message)
            fake_smoke.assert_called_once_with(
                repo_root.resolve(),
                from_ref="v0.1.4-public-alpha",
                to_ref="HEAD",
            )

    def test_release_check_preserves_upgrade_smoke_failure_diagnostics(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = self.create_release_repo(Path(temp_dir))

            def fake_run(command, **kwargs):
                return subprocess.CompletedProcess(command, 0, stdout="ok\n", stderr="")

            failed_step = SimpleNamespace(
                id="checkout_previous_ref",
                status="FAIL",
                message="Command failed with exit code 1.",
                command="git checkout missing-tag",
                path="/tmp/previous",
                stdout_tail="checkout stdout",
                stderr_tail="checkout stderr",
            )
            fake_report = SimpleNamespace(
                ok=False,
                failed=[failed_step],
                previous_version={},
                current_version={},
            )

            with patch("agentic_os.release_check.subprocess.run", side_effect=fake_run):
                with patch("agentic_os.release_check.release_upgrade_smoke", return_value=fake_report):
                    report = release_check(
                        repo_root,
                        upgrade_smoke=True,
                        from_ref="missing-tag",
                        to_ref="HEAD",
                    )

            step = report.steps[-1]
            self.assertFalse(report.ok)
            self.assertEqual("release_upgrade_smoke", step.id)
            self.assertEqual("git checkout missing-tag", step.command)
            self.assertEqual("/tmp/previous", step.path)
            self.assertEqual("checkout stdout", step.stdout_tail)
            self.assertEqual("checkout stderr", step.stderr_tail)
            self.assertIn("checkout_previous_ref", step.message)

    def test_release_check_can_include_fresh_user_smoke_when_requested(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = self.create_release_repo(Path(temp_dir))

            def fake_run(command, **kwargs):
                return subprocess.CompletedProcess(command, 0, stdout="ok\n", stderr="")

            fake_report = SimpleNamespace(ok=True, failed=[], project_id="fresh-user-demo")

            with patch("agentic_os.release_check.subprocess.run", side_effect=fake_run):
                with patch("agentic_os.release_check.fresh_user_smoke", return_value=fake_report) as fake_smoke:
                    report = release_check(repo_root, fresh_user_smoke_gate=True)

            self.assertTrue(report.ok)
            self.assertEqual("fresh_user_smoke", report.steps[-1].id)
            self.assertIn("fresh-user-demo", report.steps[-1].message)
            fake_smoke.assert_called_once_with(repo_root.resolve(), launcher=repo_root.resolve() / "bin/aos")

    def test_release_check_preserves_fresh_user_smoke_failure_diagnostics(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = self.create_release_repo(Path(temp_dir))

            def fake_run(command, **kwargs):
                return subprocess.CompletedProcess(command, 0, stdout="ok\n", stderr="")

            failed_step = SimpleNamespace(
                id="compile_codex",
                message="Command failed with exit code 1.",
                command="/tmp/aos compile codex",
                path="/tmp/demo-project",
                stdout_tail="compile stdout",
                stderr_tail="compile stderr",
                next_action="Run the failing compile command manually.",
            )
            fake_report = SimpleNamespace(ok=False, failed=[failed_step], project_id="fresh-user-demo")

            with patch("agentic_os.release_check.subprocess.run", side_effect=fake_run):
                with patch("agentic_os.release_check.fresh_user_smoke", return_value=fake_report):
                    report = release_check(repo_root, fresh_user_smoke_gate=True)

            step = report.steps[-1]
            self.assertFalse(report.ok)
            self.assertEqual("fresh_user_smoke", step.id)
            self.assertEqual("/tmp/aos compile codex", step.command)
            self.assertEqual("/tmp/demo-project", step.path)
            self.assertEqual("compile stdout", step.stdout_tail)
            self.assertEqual("compile stderr", step.stderr_tail)
            self.assertEqual("Run the failing compile command manually.", step.next_action)
            self.assertIn("compile_codex", step.message)
            self.assertIn("Next action:", step.message)

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
            self.write_manifest(repo_root)

            with patch("agentic_os.release_check.subprocess.run") as fake_run:
                fake_run.return_value = subprocess.CompletedProcess([], 0, stdout="ok\n", stderr="")
                report = release_check(repo_root)

            self.assertFalse(report.ok)
            failed = [step for step in report.steps if step.status == "FAIL"]
            self.assertEqual(["version_consistency"], [step.id for step in failed])
            self.assertIn("expected v0.1.5-public-alpha", failed[0].message)

    def test_release_check_cli_outputs_json(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = self.create_release_repo(Path(temp_dir))
            stdout = io.StringIO()

            fake_report = SimpleNamespace(ok=True, failed=[], project_id="fresh-user-demo")

            with patch("agentic_os.release_check.subprocess.run") as fake_run:
                fake_run.return_value = subprocess.CompletedProcess([], 0, stdout="ok\n", stderr="")
                with patch("agentic_os.release_check.fresh_user_smoke", return_value=fake_report):
                    code = main(
                        [
                            "release-check",
                            "--repo-root",
                            str(repo_root),
                            "--fresh-user-smoke",
                            "--json",
                        ],
                        stdout=stdout,
                    )

            payload = json.loads(stdout.getvalue())
            self.assertEqual(0, code)
            self.assertTrue(payload["ok"])
            self.assertEqual(7, payload["passed_count"])
            self.assertEqual(0, payload["failed_count"])
            self.assertEqual(
                [
                    "version_consistency",
                    "unit_tests",
                    "readiness_smoke",
                    "distribution_check",
                    "release_manifest",
                    "install_manager_dry_run",
                    "fresh_user_smoke",
                ],
                [step["id"] for step in payload["steps"]],
            )

    def test_release_check_cli_can_skip_release_manifest(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = self.create_release_repo(Path(temp_dir))
            (repo_root / "public-release-manifest.json").unlink()
            stdout = io.StringIO()

            with patch("agentic_os.release_check.subprocess.run") as fake_run:
                fake_run.return_value = subprocess.CompletedProcess([], 0, stdout="ok\n", stderr="")
                code = main(
                    [
                        "release-check",
                        "--repo-root",
                        str(repo_root),
                        "--skip-release-manifest",
                        "--json",
                    ],
                    stdout=stdout,
                )

            payload = json.loads(stdout.getvalue())
            self.assertEqual(0, code)
            self.assertTrue(payload["ok"])
            self.assertNotIn("release_manifest", [step["id"] for step in payload["steps"]])

    def create_release_repo(self, repo_root: Path) -> Path:
        (repo_root / "src/agentic_os").mkdir(parents=True)
        (repo_root / "src/agentic_os/version.py").write_text(
            'VERSION = "0.1.5"\nRELEASE_CHANNEL = "public-alpha"\n',
            encoding="utf-8",
        )
        (repo_root / "pyproject.toml").write_text(
            '[project]\nname = "agentic-os"\nversion = "0.1.5"\n',
            encoding="utf-8",
        )
        (repo_root / "CHANGELOG.md").write_text(
            "# Changelog\n\n## v0.1.5-public-alpha\n\n- Release manifest checksums.\n",
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
        self.write_manifest(repo_root)
        return repo_root

    def write_manifest(self, repo_root: Path) -> None:
        files = sorted(
            path.relative_to(repo_root).as_posix()
            for path in repo_root.rglob("*")
            if path.is_file() and path.name != "public-release-manifest.json"
        )
        checksums = {
            relative: hashlib.sha256((repo_root / relative).read_bytes()).hexdigest()
            for relative in files
        }
        (repo_root / "public-release-manifest.json").write_text(
            json.dumps({"files": files, "sha256": checksums}, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    unittest.main()
