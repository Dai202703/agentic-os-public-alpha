import tempfile
import unittest
from pathlib import Path

from agentic_os.security import scan_private_data


class SecurityScanTests(unittest.TestCase):
    def test_scan_private_data_reports_secret_like_strings(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "notes.md"
            path.write_text(
                "token: sk-test12345678901234567890\nOPENAI_API_KEY=abc\n",
                encoding="utf-8",
            )

            findings = scan_private_data([path])

            self.assertEqual(["SECRET_PATTERN", "SECRET_PATTERN"], [finding.code for finding in findings])
            self.assertTrue(all(finding.path == str(path) for finding in findings))

    def test_scan_private_data_reports_local_path_patterns_with_line_numbers(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "AGENTS.md"
            path.write_text(
                "\n".join(
                    [
                        "Project notes",
                        "Home path: /Users/dai/Documents/private-notes.md",
                        "Temp path: /private/var/folders/cache.txt",
                        "Var path: /var/folders/ft/session.log",
                        "Tmp path: /tmp/agentic-os-debug.log",
                    ]
                ),
                encoding="utf-8",
            )

            findings = scan_private_data([path])

            self.assertEqual(
                [
                    "LOCAL_PATH_PATTERN",
                    "LOCAL_PATH_PATTERN",
                    "LOCAL_PATH_PATTERN",
                    "LOCAL_PATH_PATTERN",
                ],
                [finding.code for finding in findings],
            )
            self.assertEqual([2, 3, 4, 5], [finding.line for finding in findings])

    def test_scan_private_data_reports_private_memory_references_with_line_numbers(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "CLAUDE.md"
            path.write_text(
                "Generated instructions\nSee memory/project-state/demo.md for private state.\n",
                encoding="utf-8",
            )

            findings = scan_private_data([path])

            self.assertEqual(["PRIVATE_MEMORY_REFERENCE"], [finding.code for finding in findings])
            self.assertEqual([2], [finding.line for finding in findings])

    def test_scan_private_data_reports_sensitive_filenames(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env.local"
            env_path.write_text("DEBUG=true\n", encoding="utf-8")
            credentials_path = Path(temp_dir) / "credentials.json"
            credentials_path.write_text("{}\n", encoding="utf-8")

            findings = scan_private_data([env_path, credentials_path])

            self.assertEqual(["SENSITIVE_FILENAME", "SENSITIVE_FILENAME"], [finding.code for finding in findings])
            self.assertEqual([str(env_path), str(credentials_path)], [finding.path for finding in findings])

    def test_scan_private_data_recurses_directories_without_following_symlinks(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "scan-root"
            outside = Path(temp_dir) / "outside"
            nested = root / "nested"
            root.mkdir()
            outside.mkdir()
            nested.mkdir()
            env_path = nested / ".env.local"
            env_path.write_text("OPENAI_API_KEY=abc\n", encoding="utf-8")
            outside_env = outside / ".env.local"
            outside_env.write_text("OPENAI_API_KEY=outside\n", encoding="utf-8")
            symlink_paths: list[Path] = []
            try:
                file_link = root / "linked-env"
                file_link.symlink_to(outside_env)
                symlink_paths.append(file_link)
            except (NotImplementedError, OSError):
                pass
            try:
                directory_link = root / "linked-dir"
                directory_link.symlink_to(outside, target_is_directory=True)
                symlink_paths.append(directory_link)
            except (NotImplementedError, OSError):
                pass

            findings = scan_private_data([root])

            env_codes = [finding.code for finding in findings if finding.path == str(env_path)]
            self.assertIn("SENSITIVE_FILENAME", env_codes)
            self.assertIn("SECRET_PATTERN", env_codes)
            for symlink_path in symlink_paths:
                self.assertFalse(
                    any(
                        finding.path == str(symlink_path)
                        or finding.path.startswith(f"{symlink_path}/")
                        for finding in findings
                    )
                )

    def test_scan_private_data_ignores_private_memory_references_in_yaml_configs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "project.yaml"
            path.write_text(
                """memory:
  project_state: "memory/project-state/demo.md"
""",
                encoding="utf-8",
            )

            findings = scan_private_data([path])

            self.assertNotIn("PRIVATE_MEMORY_REFERENCE", [finding.code for finding in findings])

    def test_scan_private_data_skips_missing_directories_and_binary_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            binary_path = root / "image.bin"
            binary_path.write_bytes(b"\x00\xff\x00\xff")

            findings = scan_private_data([root, root / "missing.txt", binary_path])

            self.assertEqual([], findings)


if __name__ == "__main__":
    unittest.main()
