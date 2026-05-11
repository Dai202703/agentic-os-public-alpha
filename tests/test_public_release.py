import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from agentic_os.cli import main
from agentic_os.public_audit import public_audit
from agentic_os.public_export import public_export


class PublicReleaseTests(unittest.TestCase):
    def test_public_audit_fails_on_private_data_in_git_history(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            self.git(repo_root, "init")
            (repo_root / "README.md").write_text(
                "Private path: /Users/dai/.agentic-os/memory/sessions/private.md\n",
                encoding="utf-8",
            )
            self.git(repo_root, "add", "README.md")
            self.git(repo_root, "commit", "-m", "add private readme")
            (repo_root / "README.md").write_text("Public readme\n", encoding="utf-8")
            self.git(repo_root, "add", "README.md")
            self.git(repo_root, "commit", "-m", "clean readme")

            report = public_audit(repo_root)

            self.assertFalse(report.ok)
            self.assertEqual(["history"], [finding.source for finding in report.findings])
            self.assertEqual(["LOCAL_PATH_PATTERN"], [finding.code for finding in report.findings])

    def test_public_audit_passes_when_tree_and_history_are_clean(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            self.git(repo_root, "init")
            (repo_root / "README.md").write_text("Public readme\n", encoding="utf-8")
            self.git(repo_root, "add", "README.md")
            self.git(repo_root, "commit", "-m", "public readme")

            report = public_audit(repo_root)

            self.assertTrue(report.ok)
            self.assertEqual([], report.findings)

    def test_public_export_copies_shareable_files_only(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = self.create_source_repo(Path(temp_dir) / "source")
            output = Path(temp_dir) / "public"

            manifest = public_export(repo_root, output)

            self.assertTrue((output / ".gitignore").is_file())
            self.assertTrue((output / "README.md").is_file())
            self.assertTrue((output / "src/agentic_os/cli.py").is_file())
            self.assertTrue((output / "tests/test_cli.py").is_file())
            self.assertFalse((output / "src/agentic_os/__pycache__").exists())
            self.assertFalse((output / "tests/__pycache__").exists())
            self.assertFalse((output / "AGENTS.md").exists())
            self.assertFalse((output / ".agentic-os").exists())
            self.assertIn(".gitignore", manifest.files)
            self.assertIn("README.md", manifest.files)
            self.assertIn("src/agentic_os/cli.py", manifest.files)

    def test_public_release_cli_outputs_json_for_audit_and_export(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = self.create_source_repo(Path(temp_dir) / "source")
            output = Path(temp_dir) / "public"
            audit_stdout = io.StringIO()
            export_stdout = io.StringIO()

            audit_code = main(["public-audit", "--repo-root", str(repo_root), "--json"], stdout=audit_stdout)
            export_code = main(
                ["public-export", "--repo-root", str(repo_root), "--output", str(output), "--json"],
                stdout=export_stdout,
            )

            audit_payload = json.loads(audit_stdout.getvalue())
            export_payload = json.loads(export_stdout.getvalue())
            self.assertEqual(1, audit_code)
            self.assertFalse(audit_payload["ok"])
            self.assertEqual(0, export_code)
            self.assertTrue(export_payload["ok"])
            self.assertEqual(str(output.resolve()), export_payload["output_root"])

    def create_source_repo(self, repo_root: Path) -> Path:
        (repo_root / "src/agentic_os").mkdir(parents=True)
        (repo_root / "src/agentic_os/cli.py").write_text("def main():\n    return 0\n", encoding="utf-8")
        (repo_root / "src/agentic_os/__pycache__").mkdir()
        (repo_root / "src/agentic_os/__pycache__/cli.cpython-311.pyc").write_bytes(b"cache")
        (repo_root / "tests").mkdir()
        (repo_root / "tests/test_cli.py").write_text("import unittest\n", encoding="utf-8")
        (repo_root / "tests/__pycache__").mkdir()
        (repo_root / "tests/__pycache__/test_cli.cpython-311.pyc").write_bytes(b"cache")
        (repo_root / "docs").mkdir()
        (repo_root / "docs/public-release.md").write_text("Public policy\n", encoding="utf-8")
        (repo_root / "scripts").mkdir()
        (repo_root / "scripts/readiness_smoke.py").write_text("#!/usr/bin/env python3\n", encoding="utf-8")
        (repo_root / "bin").mkdir()
        (repo_root / "bin/aos").write_text("#!/usr/bin/env sh\n", encoding="utf-8")
        (repo_root / "README.md").write_text("Public readme\n", encoding="utf-8")
        (repo_root / ".gitignore").write_text("__pycache__/\n*.py[cod]\n", encoding="utf-8")
        (repo_root / "pyproject.toml").write_text("[project]\nname = \"agentic-os\"\n", encoding="utf-8")
        (repo_root / ".agentic-os").mkdir()
        (repo_root / ".agentic-os/project.yaml").write_text("id: private\n", encoding="utf-8")
        (repo_root / "AGENTS.md").write_text("# generated\n", encoding="utf-8")
        return repo_root

    def git(self, cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                "git",
                "-c",
                "user.email=public-audit@example.invalid",
                "-c",
                "user.name=Public Audit Test",
                *args,
            ],
            cwd=cwd,
            check=True,
            text=True,
            capture_output=True,
        )


if __name__ == "__main__":
    unittest.main()
