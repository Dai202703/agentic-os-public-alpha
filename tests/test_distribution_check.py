import io
import json
import tempfile
import unittest
from pathlib import Path

from agentic_os.cli import main
from agentic_os.distribution import distribution_check


class DistributionCheckTests(unittest.TestCase):
    def test_clean_shareable_repo_passes_distribution_check(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            (repo_root / "README.md").write_text(
                "Use /tmp/aos-demo for disposable examples.\n",
                encoding="utf-8",
            )
            source_dir = repo_root / "src/agentic_os"
            source_dir.mkdir(parents=True)
            (source_dir / "templates.py").write_text(
                'STARTER_FILES = {"core/identity/user.md": "# User Identity"}\n',
                encoding="utf-8",
            )
            (source_dir / "security.py").write_text(
                'LOCAL_PATH_PATTERN = r"(?:/Users/|/private/var/|/var/folders/)"\n',
                encoding="utf-8",
            )
            tests_dir = repo_root / "tests"
            tests_dir.mkdir()
            (tests_dir / "test_security.py").write_text(
                'fixture = "OPENAI_API_KEY=private-test-value"\n',
                encoding="utf-8",
            )

            report = distribution_check(repo_root)

            self.assertTrue(report.ok)
            self.assertEqual([], report.issues)

    def test_private_os_home_and_generated_outputs_fail_distribution_check(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            (repo_root / ".agentic-os").mkdir()
            (repo_root / ".agentic-os/project.yaml").write_text(
                "id: private-project\n",
                encoding="utf-8",
            )
            (repo_root / "AGENTS.md").write_text(
                "# Generated provider output\n",
                encoding="utf-8",
            )

            report = distribution_check(repo_root)

            self.assertFalse(report.ok)
            self.assertEqual(
                ["PRIVATE_OS_HOME_PATH", "GENERATED_PROVIDER_OUTPUT"],
                [issue.code for issue in report.issues],
            )

    def test_distribution_check_allows_tmp_examples_but_flags_user_paths(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            (repo_root / "README.md").write_text(
                "\n".join(
                    [
                        "Temporary example: /tmp/aos-demo",
                        "Private path: /Users/dai/.agentic-os/memory/sessions/private.md",
                    ]
                ),
                encoding="utf-8",
            )

            report = distribution_check(repo_root)

            self.assertFalse(report.ok)
            self.assertEqual(["LOCAL_PATH_PATTERN"], [issue.code for issue in report.issues])
            self.assertEqual([2], [issue.line for issue in report.issues])

    def test_distribution_check_cli_outputs_json(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            (repo_root / ".env.local").write_text(
                "OPENAI_API_KEY=private\n",
                encoding="utf-8",
            )
            stdout = io.StringIO()

            code = main(
                ["distribution-check", "--repo-root", str(repo_root), "--json"],
                stdout=stdout,
            )

            payload = json.loads(stdout.getvalue())
            self.assertEqual(1, code)
            self.assertFalse(payload["ok"])
            self.assertEqual(["SENSITIVE_FILENAME", "SECRET_PATTERN"], [issue["code"] for issue in payload["issues"]])


if __name__ == "__main__":
    unittest.main()
