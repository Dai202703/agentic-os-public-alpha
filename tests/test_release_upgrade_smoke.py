import io
import json
import shutil
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

from agentic_os.cli import main
from agentic_os.release_upgrade_smoke import release_upgrade_smoke


class ReleaseUpgradeSmokeTests(unittest.TestCase):
    def setUp(self):
        self.repo_root = Path(__file__).resolve().parents[1]

    def test_upgrade_smoke_installs_updates_and_rolls_back_between_refs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            release_repo = self.create_two_release_repo(Path(temp_dir))

            report = release_upgrade_smoke(
                release_repo,
                from_ref="v1.0.0-public-alpha",
                to_ref="v1.1.0-public-alpha",
            )

            self.assertTrue(report.ok, [step.message for step in report.failed])
            self.assertEqual("1.0.0", report.previous_version["version"])
            self.assertEqual("v1.0.0-public-alpha", report.previous_version["release_tag"])
            self.assertEqual("1.1.0", report.current_version["version"])
            self.assertEqual("v1.1.0-public-alpha", report.current_version["release_tag"])
            self.assertEqual(
                [
                    "checkout_previous_ref",
                    "checkout_current_ref",
                    "install_previous",
                    "verify_previous_target",
                    "verify_previous_version",
                    "update_current",
                    "verify_current_target",
                    "verify_current_version",
                    "rollback_previous",
                    "verify_rollback_target",
                    "verify_rollback_version",
                ],
                [step.id for step in report.steps],
            )

    def test_release_upgrade_smoke_cli_outputs_json(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            release_repo = self.create_two_release_repo(Path(temp_dir))
            stdout = io.StringIO()

            code = main(
                [
                    "release-upgrade-smoke",
                    "--repo-root",
                    str(release_repo),
                    "--from-ref",
                    "v1.0.0-public-alpha",
                    "--to-ref",
                    "v1.1.0-public-alpha",
                    "--json",
                ],
                stdout=stdout,
            )

            payload = json.loads(stdout.getvalue())
            self.assertEqual(0, code)
            self.assertTrue(payload["ok"])
            self.assertEqual("v1.0.0-public-alpha", payload["from_ref"])
            self.assertEqual("v1.1.0-public-alpha", payload["to_ref"])
            self.assertEqual("1.0.0", payload["previous_version"]["version"])
            self.assertEqual("1.1.0", payload["current_version"]["version"])

    def create_two_release_repo(self, temp_root: Path) -> Path:
        release_repo = temp_root / "release-repo"
        release_repo.mkdir()
        self.git(release_repo, "init")
        self.git(release_repo, "config", "user.email", "aos-test@example.com")
        self.git(release_repo, "config", "user.name", "AOS Test")
        self.git(release_repo, "config", "commit.gpgsign", "false")

        self.write_release_tree(release_repo, "1.0.0")
        self.git(release_repo, "add", ".")
        self.git(release_repo, "commit", "-m", "release 1.0.0")
        self.git(release_repo, "tag", "v1.0.0-public-alpha")

        self.write_release_tree(release_repo, "1.1.0")
        self.git(release_repo, "add", ".")
        self.git(release_repo, "commit", "-m", "release 1.1.0")
        self.git(release_repo, "tag", "v1.1.0-public-alpha")
        return release_repo

    def write_release_tree(self, release_repo: Path, version: str) -> None:
        (release_repo / "bin").mkdir(exist_ok=True)
        (release_repo / "scripts").mkdir(exist_ok=True)
        (release_repo / "src/agentic_os").mkdir(parents=True, exist_ok=True)
        (release_repo / "src/agentic_os/version.py").write_text(
            f'VERSION = "{version}"\nRELEASE_CHANNEL = "public-alpha"\n',
            encoding="utf-8",
        )
        shutil.copy2(
            self.repo_root / "scripts/manage_global_aos.py",
            release_repo / "scripts/manage_global_aos.py",
        )
        (release_repo / "scripts/manage_global_aos.py").chmod(0o755)
        launcher = release_repo / "bin/aos"
        launcher.write_text(self.fake_launcher_source(), encoding="utf-8")
        launcher.chmod(0o755)

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
            version_file = root / "src/agentic_os/version.py"
            content = version_file.read_text(encoding="utf-8")

            def read_value(name):
                match = re.search(rf'(?m)^{name}\\s*=\\s*["\\']([^"\\']+)["\\']\\s*$', content)
                if not match:
                    raise SystemExit(f"missing {name}")
                return match.group(1)

            version = read_value("VERSION")
            release_channel = read_value("RELEASE_CHANNEL")
            release_tag = f"v{version}-{release_channel}" if release_channel else f"v{version}"

            if sys.argv[1:] == ["version", "--json"]:
                print(json.dumps({
                    "command_path": str(pathlib.Path(__file__).resolve()),
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
