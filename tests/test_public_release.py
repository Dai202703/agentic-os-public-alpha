import io
import json
import re
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
            repo_root = self.create_repo_with_private_history(Path(temp_dir))

            report = public_audit(repo_root)

            self.assertFalse(report.ok)
            self.assertEqual(["history", "history"], [finding.source for finding in report.findings])
            self.assertEqual(
                ["LOCAL_PATH_PATTERN", "PRIVATE_MEMORY_REFERENCE"],
                [finding.code for finding in report.findings],
            )

    def test_public_audit_tree_only_passes_when_history_has_private_data(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = self.create_repo_with_private_history(Path(temp_dir))

            report = public_audit(repo_root, include_history=False)

            self.assertTrue(report.ok)
            self.assertFalse(report.history_scanned)
            self.assertEqual([], report.findings)

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
            self.assertTrue((output / "docs/assets/aos-public-alpha-flow.svg").is_file())
            self.assertTrue((output / "docs/assets/aos-first-run-demo.svg").is_file())
            self.assertTrue((output / "docs/demo.md").is_file())
            self.assertTrue((output / "docs/memory-workflows.md").is_file())
            self.assertTrue((output / "scripts/install.ps1").is_file())
            self.assertTrue((output / "scripts/windows_install_smoke.py").is_file())
            self.assertTrue((output / "src/agentic_os/cli.py").is_file())
            self.assertTrue((output / "tests/test_cli.py").is_file())
            self.assertFalse((output / "src/agentic_os/__pycache__").exists())
            self.assertFalse((output / "tests/__pycache__").exists())
            self.assertFalse((output / "AGENTS.md").exists())
            self.assertFalse((output / ".agentic-os").exists())
            self.assertIn(".gitignore", manifest.files)
            self.assertIn("README.md", manifest.files)
            self.assertIn("docs/assets/aos-public-alpha-flow.svg", manifest.files)
            self.assertIn("docs/assets/aos-first-run-demo.svg", manifest.files)
            self.assertIn("docs/demo.md", manifest.files)
            self.assertIn("docs/memory-workflows.md", manifest.files)
            self.assertIn("scripts/install.ps1", manifest.files)
            self.assertIn("scripts/windows_install_smoke.py", manifest.files)
            self.assertIn("src/agentic_os/cli.py", manifest.files)
            manifest_payload = json.loads((output / "public-release-manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest.files, manifest_payload["files"])
            self.assertEqual(set(manifest.files), set(manifest.checksums))
            self.assertEqual(set(manifest.files), set(manifest_payload["sha256"]))
            self.assertRegex(manifest_payload["sha256"]["README.md"], re.compile(r"^[0-9a-f]{64}$"))
            self.assertRegex(
                manifest_payload["sha256"]["docs/assets/aos-public-alpha-flow.svg"],
                re.compile(r"^[0-9a-f]{64}$"),
            )
            self.assertRegex(
                manifest_payload["sha256"]["docs/assets/aos-first-run-demo.svg"],
                re.compile(r"^[0-9a-f]{64}$"),
            )
            self.assertRegex(
                manifest_payload["sha256"]["scripts/install.ps1"],
                re.compile(r"^[0-9a-f]{64}$"),
            )
            self.assertRegex(
                manifest_payload["sha256"]["scripts/windows_install_smoke.py"],
                re.compile(r"^[0-9a-f]{64}$"),
            )

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
            self.assertEqual(set(export_payload["files"]), set(export_payload["sha256"]))

    def test_public_export_rejects_symlinks_inside_exported_paths(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = self.create_source_repo(Path(temp_dir) / "source")
            outside = Path(temp_dir) / "outside-private.md"
            outside.write_text("Private path: /Users/dai/private.md\n", encoding="utf-8")
            linked = repo_root / "docs/linked-private.md"
            try:
                linked.symlink_to(outside)
            except (NotImplementedError, OSError) as error:
                self.skipTest(f"Symlink creation is unsupported: {error}")

            with self.assertRaisesRegex(ValueError, "Symlink is not allowed in public export"):
                public_export(repo_root, Path(temp_dir) / "public")

    def test_public_export_rejects_binary_files_inside_exported_paths(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = self.create_source_repo(Path(temp_dir) / "source")
            (repo_root / "docs/payload.bin").write_bytes(b"\x00\xffprivate")

            with self.assertRaisesRegex(ValueError, "Binary or non-UTF-8 file is not allowed in public export"):
                public_export(repo_root, Path(temp_dir) / "public")

    def test_public_audit_cli_tree_only_skips_history_scan(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = self.create_repo_with_private_history(Path(temp_dir))
            audit_stdout = io.StringIO()

            audit_code = main(
                ["public-audit", "--repo-root", str(repo_root), "--tree-only", "--json"],
                stdout=audit_stdout,
            )

            audit_payload = json.loads(audit_stdout.getvalue())
            self.assertEqual(0, audit_code)
            self.assertTrue(audit_payload["ok"])
            self.assertFalse(audit_payload["history_scanned"])
            self.assertEqual([], audit_payload["findings"])

    def create_source_repo(self, repo_root: Path) -> Path:
        (repo_root / "src/agentic_os").mkdir(parents=True)
        (repo_root / "src/agentic_os/cli.py").write_text("def main():\n    return 0\n", encoding="utf-8")
        (repo_root / "src/agentic_os/__pycache__").mkdir()
        (repo_root / "src/agentic_os/__pycache__/cli.cpython-311.pyc").write_bytes(b"cache")
        (repo_root / "tests").mkdir()
        (repo_root / "tests/test_cli.py").write_text("import unittest\n", encoding="utf-8")
        (repo_root / "tests/__pycache__").mkdir()
        (repo_root / "tests/__pycache__/test_cli.cpython-311.pyc").write_bytes(b"cache")
        (repo_root / "docs/assets").mkdir(parents=True)
        (repo_root / "docs/assets/aos-public-alpha-flow.svg").write_text(
            "<svg><title>AOS flow</title><desc>Public demo</desc></svg>\n",
            encoding="utf-8",
        )
        (repo_root / "docs/assets/aos-first-run-demo.svg").write_text(
            "<svg><title>AOS first run</title><desc>Public demo</desc></svg>\n",
            encoding="utf-8",
        )
        (repo_root / "docs/demo.md").write_text("# Demo\n", encoding="utf-8")
        (repo_root / "docs/memory-workflows.md").write_text("# Memory Workflows\n", encoding="utf-8")
        (repo_root / "docs/public-release.md").write_text("Public policy\n", encoding="utf-8")
        (repo_root / "scripts").mkdir()
        (repo_root / "scripts/readiness_smoke.py").write_text("#!/usr/bin/env python3\n", encoding="utf-8")
        (repo_root / "scripts/install.ps1").write_text("[CmdletBinding()]\n", encoding="utf-8")
        (repo_root / "scripts/windows_install_smoke.py").write_text("#!/usr/bin/env python3\n", encoding="utf-8")
        (repo_root / "bin").mkdir()
        (repo_root / "bin/aos").write_text("#!/usr/bin/env sh\n", encoding="utf-8")
        (repo_root / "README.md").write_text("Public readme\n", encoding="utf-8")
        (repo_root / ".gitignore").write_text("__pycache__/\n*.py[cod]\n", encoding="utf-8")
        (repo_root / "pyproject.toml").write_text("[project]\nname = \"agentic-os\"\n", encoding="utf-8")
        (repo_root / ".agentic-os").mkdir()
        (repo_root / ".agentic-os/project.yaml").write_text("id: private\n", encoding="utf-8")
        (repo_root / "AGENTS.md").write_text("# generated\n", encoding="utf-8")
        return repo_root

    def create_repo_with_private_history(self, repo_root: Path) -> Path:
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
