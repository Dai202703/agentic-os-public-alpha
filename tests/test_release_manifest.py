import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from agentic_os.release_manifest import release_manifest_check


class ReleaseManifestTests(unittest.TestCase):
    def test_release_manifest_passes_when_files_and_checksums_match(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            self.write_file(repo_root, "README.md", "Public readme\n")
            self.write_file(repo_root, "src/agentic_os/cli.py", "def main():\n    return 0\n")
            self.write_manifest(repo_root, ["README.md", "src/agentic_os/cli.py"])

            report = release_manifest_check(repo_root)

            self.assertTrue(report.ok)
            self.assertEqual([], report.issues)
            self.assertEqual(2, report.files_count)

    def test_release_manifest_fails_when_checksum_is_stale(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            self.write_file(repo_root, "README.md", "Public readme\n")
            self.write_manifest(repo_root, ["README.md"])
            self.write_file(repo_root, "README.md", "Changed readme\n")

            report = release_manifest_check(repo_root)

            self.assertFalse(report.ok)
            self.assertEqual(["CHECKSUM_MISMATCH"], [issue.code for issue in report.issues])
            self.assertEqual("README.md", report.issues[0].path)

    def test_release_manifest_fails_when_listed_file_is_missing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            self.write_file(repo_root, "README.md", "Public readme\n")
            self.write_manifest(repo_root, ["README.md"])
            (repo_root / "README.md").unlink()

            report = release_manifest_check(repo_root)

            self.assertFalse(report.ok)
            self.assertEqual(["MANIFEST_FILE_MISSING"], [issue.code for issue in report.issues])

    def test_release_manifest_fails_when_actual_file_is_unlisted(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            self.write_file(repo_root, "README.md", "Public readme\n")
            self.write_file(repo_root, "SECURITY.md", "Security policy\n")
            self.write_manifest(repo_root, ["README.md"])

            report = release_manifest_check(repo_root)

            self.assertFalse(report.ok)
            self.assertEqual(["MANIFEST_FILE_UNLISTED"], [issue.code for issue in report.issues])
            self.assertEqual("SECURITY.md", report.issues[0].path)

    def test_release_manifest_fails_when_checksum_entry_has_no_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            self.write_file(repo_root, "README.md", "Public readme\n")
            self.write_manifest(repo_root, ["README.md"])
            payload = json.loads((repo_root / "public-release-manifest.json").read_text(encoding="utf-8"))
            payload["sha256"]["ghost.md"] = "0" * 64
            (repo_root / "public-release-manifest.json").write_text(
                json.dumps(payload, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )

            report = release_manifest_check(repo_root)

            self.assertFalse(report.ok)
            self.assertEqual(["CHECKSUM_FILE_UNLISTED"], [issue.code for issue in report.issues])
            self.assertEqual("ghost.md", report.issues[0].path)

    def write_file(self, repo_root: Path, relative: str, content: str) -> None:
        path = repo_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def write_manifest(self, repo_root: Path, files: list[str]) -> None:
        checksums = {}
        for relative in files:
            checksums[relative] = hashlib.sha256((repo_root / relative).read_bytes()).hexdigest()
        (repo_root / "public-release-manifest.json").write_text(
            json.dumps({"files": files, "sha256": checksums}, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    unittest.main()
