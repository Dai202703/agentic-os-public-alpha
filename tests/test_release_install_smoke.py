import io
import json
import os
import shutil
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest.mock import patch

from agentic_os.cli import main
from agentic_os.release_install_smoke import release_install_smoke


class ReleaseInstallSmokeTests(unittest.TestCase):
    def setUp(self):
        self.repo_root = Path(__file__).resolve().parents[1]

    def test_release_install_smoke_fetches_tag_installs_and_reports_version(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            release_repo = self.create_release_repo(Path(temp_dir), metadata_version="1.2.3")

            report = release_install_smoke(
                source=release_repo,
                ref="v1.2.3-public-alpha",
            )

        self.assertTrue(report.ok, [step.message for step in report.failed])
        self.assertEqual("refs/tags/v1.2.3-public-alpha", report.normalized_ref)
        self.assertEqual("v1.2.3-public-alpha", report.expected_tag)
        self.assertEqual("1.2.3", report.installed_version["version"])
        self.assertEqual("v1.2.3-public-alpha", report.installed_version["release_tag"])
        self.assertEqual(
            [
                "fetch_ref",
                "checkout_ref",
                "read_expected_version",
                "verify_ref_matches_version",
                "install_release",
                "verify_install_target",
                "verify_installed_version",
            ],
            [step.id for step in report.steps],
        )

    def test_release_install_smoke_accepts_full_refs_tags_ref(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            release_repo = self.create_release_repo(Path(temp_dir), metadata_version="1.2.3")

            report = release_install_smoke(
                source=release_repo,
                ref="refs/tags/v1.2.3-public-alpha",
            )

        self.assertTrue(report.ok, [step.message for step in report.failed])
        self.assertEqual("refs/tags/v1.2.3-public-alpha", report.normalized_ref)
        self.assertEqual("v1.2.3-public-alpha", report.expected_tag)

    def test_release_install_smoke_fails_when_tag_and_metadata_disagree(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            release_repo = self.create_release_repo(
                Path(temp_dir),
                metadata_version="1.2.2",
                tag_name="v1.2.3-public-alpha",
            )

            report = release_install_smoke(
                source=release_repo,
                ref="v1.2.3-public-alpha",
            )

        self.assertFalse(report.ok)
        self.assertEqual("verify_ref_matches_version", report.failed[0].id)
        self.assertIn("v1.2.2-public-alpha", report.failed[0].message)
        self.assertIn("expected v1.2.3-public-alpha", report.failed[0].message)

    def test_release_install_smoke_fails_when_expected_tag_does_not_match(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            release_repo = self.create_release_repo(Path(temp_dir), metadata_version="1.2.3")

            report = release_install_smoke(
                source=release_repo,
                ref="v1.2.3-public-alpha",
                expected_tag="v9.9.9-public-alpha",
            )

        self.assertFalse(report.ok)
        self.assertEqual("verify_ref_matches_version", report.failed[0].id)
        self.assertIn("expected v9.9.9-public-alpha", report.failed[0].message)

    def test_release_install_smoke_preserves_fetch_failure_diagnostics(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            release_repo = self.create_release_repo(Path(temp_dir), metadata_version="1.2.3")

            report = release_install_smoke(
                source=release_repo,
                ref="v9.9.9-public-alpha",
            )

        self.assertFalse(report.ok)
        self.assertEqual("fetch_ref", report.failed[0].id)
        self.assertIsNotNone(report.failed[0].command)
        self.assertIsNotNone(report.failed[0].stderr_tail)
        self.assertIn("v9.9.9-public-alpha", report.failed[0].command)
        self.assertIn("Check that the release source and tag exist", report.failed[0].next_action)

    def test_release_install_smoke_ignores_ambient_install_environment(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            release_repo = self.create_release_repo(temp_root, metadata_version="1.2.3")
            marker = temp_root / "readiness-ran.txt"
            wrong_launcher = temp_root / "wrong-aos"
            wrong_launcher.write_text("#!/usr/bin/env sh\nexit 99\n", encoding="utf-8")
            wrong_launcher.chmod(0o755)

            with patch.dict(
                os.environ,
                {
                    "AOS_INSTALL_LAUNCHER": str(wrong_launcher),
                    "AOS_INSTALL_SKIP_CHECKS": "1",
                    "AOS_FAKE_READINESS_MARKER": str(marker),
                },
            ):
                report = release_install_smoke(
                    source=release_repo,
                    ref="v1.2.3-public-alpha",
                )
            marker_was_written = marker.is_file()

        self.assertTrue(report.ok, [step.message for step in report.failed])
        self.assertTrue(marker_was_written)

    def test_release_install_smoke_reports_subprocess_timeout(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            release_repo = self.create_release_repo(Path(temp_dir), metadata_version="1.2.3")

            with patch(
                "agentic_os.release_install_smoke.subprocess.run",
                side_effect=subprocess.TimeoutExpired(["git", "init"], 1),
            ):
                report = release_install_smoke(
                    source=release_repo,
                    ref="v1.2.3-public-alpha",
                )

        self.assertFalse(report.ok)
        self.assertEqual("fetch_ref", report.failed[0].id)
        self.assertIn("timed out", report.failed[0].message)
        self.assertIn("retry release-install-smoke", report.failed[0].next_action)

    def test_release_install_smoke_cli_outputs_json(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            release_repo = self.create_release_repo(Path(temp_dir), metadata_version="1.2.3")
            stdout = io.StringIO()

            code = main(
                [
                    "release-install-smoke",
                    "--source",
                    str(release_repo),
                    "--ref",
                    "v1.2.3-public-alpha",
                    "--expected-tag",
                    "v1.2.3-public-alpha",
                    "--json",
                ],
                stdout=stdout,
            )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(0, code)
        self.assertTrue(payload["ok"])
        self.assertEqual("refs/tags/v1.2.3-public-alpha", payload["normalized_ref"])
        self.assertEqual("v1.2.3-public-alpha", payload["expected_tag"])
        self.assertEqual("v1.2.3-public-alpha", payload["installed_version"]["release_tag"])

    def create_release_repo(
        self,
        temp_root: Path,
        *,
        metadata_version: str,
        tag_name: str | None = None,
    ) -> Path:
        release_repo = temp_root / "release-repo"
        release_repo.mkdir()
        self.git(release_repo, "init")
        self.git(release_repo, "config", "user.email", "aos-test@example.com")
        self.git(release_repo, "config", "user.name", "AOS Test")
        self.git(release_repo, "config", "commit.gpgsign", "false")

        (release_repo / "bin").mkdir()
        (release_repo / "scripts").mkdir()
        (release_repo / "src/agentic_os").mkdir(parents=True)
        (release_repo / "tests").mkdir()
        (release_repo / "src/agentic_os/__init__.py").write_text("", encoding="utf-8")
        (release_repo / "src/agentic_os/version.py").write_text(
            f'VERSION = "{metadata_version}"\nRELEASE_CHANNEL = "public-alpha"\n',
            encoding="utf-8",
        )
        (release_repo / "tests/test_smoke.py").write_text(
            "import unittest\n\nclass SmokeTest(unittest.TestCase):\n    def test_smoke(self):\n        self.assertTrue(True)\n",
            encoding="utf-8",
        )
        shutil.copy2(self.repo_root / "scripts/install.sh", release_repo / "scripts/install.sh")
        shutil.copy2(
            self.repo_root / "scripts/manage_global_aos.py",
            release_repo / "scripts/manage_global_aos.py",
        )
        (release_repo / "scripts/readiness_smoke.py").write_text(
            self.fake_readiness_smoke_source(),
            encoding="utf-8",
        )
        (release_repo / "scripts/install.sh").chmod(0o755)
        (release_repo / "scripts/manage_global_aos.py").chmod(0o755)
        (release_repo / "scripts/readiness_smoke.py").chmod(0o755)
        launcher = release_repo / "bin/aos"
        launcher.write_text(self.fake_launcher_source(), encoding="utf-8")
        launcher.chmod(0o755)

        self.git(release_repo, "add", ".")
        self.git(release_repo, "commit", "-m", f"release {metadata_version}")
        self.git(release_repo, "tag", tag_name or f"v{metadata_version}-public-alpha")
        return release_repo

    def fake_readiness_smoke_source(self) -> str:
        return textwrap.dedent(
            """\
            #!/usr/bin/env python3
            import json
            import os
            import pathlib

            marker = os.environ.get("AOS_FAKE_READINESS_MARKER")
            if marker:
                pathlib.Path(marker).write_text("ran\\n", encoding="utf-8")
            print(json.dumps({"ok": True, "steps": []}, sort_keys=True))
            """
        )

    def fake_launcher_source(self) -> str:
        return textwrap.dedent(
            """\
            #!/usr/bin/env python3
            import json
            import os
            import pathlib
            import platform
            import re
            import sys

            root = pathlib.Path(__file__).resolve().parents[1]
            content = (root / "src/agentic_os/version.py").read_text(encoding="utf-8")

            def read_value(name):
                match = re.search(rf'(?m)^{name}\\s*=\\s*["\\']([^"\\']*)["\\']\\s*$', content)
                if not match:
                    raise SystemExit(f"missing {name}")
                return match.group(1)

            version = read_value("VERSION")
            release_channel = read_value("RELEASE_CHANNEL")
            release_tag = f"v{version}-{release_channel}" if release_channel else f"v{version}"

            if sys.argv[1:] == ["version", "--json"]:
                print(json.dumps({
                    "command_path": os.environ.get("AOS_COMMAND_PATH", str(pathlib.Path(__file__).resolve())),
                    "os_home": os.environ.get("AGENTIC_OS_HOME", ""),
                    "python_executable": sys.executable,
                    "python_version": platform.python_version(),
                    "release_channel": release_channel,
                    "release_tag": release_tag,
                    "version": version,
                }, sort_keys=True))
                raise SystemExit(0)

            if sys.argv[1:] == ["version"]:
                print(f"AOS version {version}")
                print(f"Release tag: {release_tag}")
                raise SystemExit(0)

            if len(sys.argv) >= 4 and sys.argv[1] == "--os-home" and sys.argv[3:] == ["init"]:
                pathlib.Path(sys.argv[2]).mkdir(parents=True, exist_ok=True)
                print(f"Initialized Agentic OS at {sys.argv[2]}")
                raise SystemExit(0)

            if len(sys.argv) >= 5 and sys.argv[1] == "--os-home" and sys.argv[3:] == ["doctor", "--summary"]:
                print("AOS home ok: 0 errors, 0 warnings")
                raise SystemExit(0)

            sys.stderr.write("unsupported fake aos command\\n")
            raise SystemExit(2)
            """
        )

    def git(self, repo: Path, *args: str) -> None:
        subprocess.run(
            ["git", *args],
            cwd=repo,
            check=True,
            text=True,
            capture_output=True,
        )


if __name__ == "__main__":
    unittest.main()
