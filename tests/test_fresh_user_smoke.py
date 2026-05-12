import io
import json
import tempfile
import textwrap
import unittest
from pathlib import Path

from agentic_os.cli import main
from agentic_os.fresh_user_smoke import fresh_user_smoke, render_fresh_user_smoke_summary


class FreshUserSmokeTests(unittest.TestCase):
    def test_fresh_user_smoke_installs_and_runs_first_project_flow(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = self.create_fake_repo(Path(temp_dir))

            report = fresh_user_smoke(repo_root)

        self.assertTrue(report.ok)
        self.assertEqual(11, len(report.steps))
        self.assertEqual([], report.failed)
        self.assertEqual(
            [
                "install_wrapper",
                "installed_version",
                "init_os_home",
                "doctor_os_home",
                "create_demo_project",
                "link_project",
                "compile_codex",
                "compile_claude",
                "compile_gemini",
                "compile_chatgpt",
            ],
            [step.id for step in report.steps[:10]],
        )
        self.assertTrue(str(report.install_dir).endswith("/bin"))
        self.assertEqual("fresh-user-demo", report.project_id)

    def test_fresh_user_smoke_cli_outputs_json(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = self.create_fake_repo(Path(temp_dir))
            stdout = io.StringIO()

            code = main(
                ["fresh-user-smoke", "--repo-root", str(repo_root), "--json"],
                stdout=stdout,
            )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(0, code)
        self.assertTrue(payload["ok"])
        self.assertEqual(11, payload["passed_count"])
        self.assertEqual(0, payload["failed_count"])
        self.assertEqual("fresh_user_onboarding", payload["steps"][-1]["id"])

    def test_failed_install_reports_output_tails_and_next_action(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = self.create_fake_repo(Path(temp_dir))
            installer = repo_root / "scripts/install.sh"
            installer.write_text(
                textwrap.dedent(
                    """\
                    #!/usr/bin/env sh
                    echo preparing install
                    echo python missing >&2
                    exit 7
                    """
                ),
                encoding="utf-8",
            )

            report = fresh_user_smoke(repo_root)

        self.assertFalse(report.ok)
        step = report.failed[0]
        self.assertEqual("install_wrapper", step.id)
        self.assertIn("exit code 7", step.message)
        self.assertIn("preparing install", step.stdout_tail)
        self.assertIn("python missing", step.stderr_tail)
        self.assertIn("Run `sh scripts/install.sh`", step.next_action)
        summary = render_fresh_user_smoke_summary(report)
        self.assertIn("first_failure=install_wrapper", summary)
        self.assertIn("next_action=Run `sh scripts/install.sh`", summary)

    def test_failed_onboarding_reports_failed_substep_ids_and_next_action(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = self.create_fake_repo(Path(temp_dir), onboarding_ok=False)

            report = fresh_user_smoke(repo_root)

        self.assertFalse(report.ok)
        step = report.failed[0]
        self.assertEqual("fresh_user_onboarding", step.id)
        self.assertIn("self_check", step.message)
        self.assertIn("private_scan", step.message)
        self.assertIn("Run the reported `aos onboarding-check` command", step.next_action)

    def create_fake_repo(self, repo_root: Path, onboarding_ok: bool = True) -> Path:
        (repo_root / "bin").mkdir()
        (repo_root / "scripts").mkdir()
        launcher = repo_root / "bin/aos"
        launcher.write_text(self.fake_aos_script(onboarding_ok=onboarding_ok), encoding="utf-8")
        launcher.chmod(0o755)
        installer = repo_root / "scripts/install.sh"
        installer.write_text(
            textwrap.dedent(
                """\
                #!/usr/bin/env sh
                set -eu
                install_dir=${AOS_INSTALL_DIR:?}
                mkdir -p "$install_dir"
                cp "$(dirname "$0")/../bin/aos" "$install_dir/aos"
                chmod +x "$install_dir/aos"
                """
            ),
            encoding="utf-8",
        )
        installer.chmod(0o755)
        return repo_root

    def fake_aos_script(self, onboarding_ok: bool = True) -> str:
        onboarding_payload = repr(
            {"ok": True, "passed_count": 4, "failed_count": 0}
            if onboarding_ok
            else {
                "ok": False,
                "passed_count": 2,
                "failed_count": 2,
                "steps": [
                    {"id": "self_check", "status": "FAIL", "message": "Self-check failed."},
                    {"id": "private_scan", "status": "FAIL", "message": "Private scan failed."},
                ],
            }
        )
        script = textwrap.dedent(
            """\
            #!/usr/bin/env python3
            import json
            import sys
            from pathlib import Path

            PROVIDER_OUTPUTS = {
                "codex": "AGENTS.md",
                "claude": "CLAUDE.md",
                "gemini": "GEMINI.md",
                "chatgpt": ".agentic-os/chatgpt-project-instructions.md",
            }

            args = sys.argv[1:]
            os_home = None
            if args[:1] == ["--os-home"]:
                os_home = Path(args[1])
                args = args[2:]

            command = args[0]
            if command == "version":
                print(json.dumps({"version": "9.9.9", "release_tag": "v9.9.9-test"}))
                raise SystemExit(0)
            if command == "init":
                os_home.mkdir(parents=True, exist_ok=True)
                print(f"Initialized Agentic OS at {os_home}")
                raise SystemExit(0)
            if command == "doctor":
                print("AOS doctor ok: 0 errors, 0 warnings")
                raise SystemExit(0)
            if command == "link-project":
                project_root = Path(args[args.index("--project-root") + 1])
                project_root.mkdir(parents=True, exist_ok=True)
                config_dir = project_root / ".agentic-os"
                config_dir.mkdir(parents=True, exist_ok=True)
                (config_dir / "project.yaml").write_text("id: fresh-user-demo\\n", encoding="utf-8")
                print(config_dir / "project.yaml")
                raise SystemExit(0)
            if command == "compile":
                provider = args[1]
                project_root = Path(args[args.index("--project-root") + 1])
                output = project_root / PROVIDER_OUTPUTS[provider]
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_text(f"# {provider}\\n", encoding="utf-8")
                print(output)
                raise SystemExit(0)
            if command == "onboarding-check":
                print(json.dumps(__ONBOARDING_PAYLOAD__))
                raise SystemExit(0)

            raise SystemExit(2)
            """
        )
        return script.replace("__ONBOARDING_PAYLOAD__", onboarding_payload)


if __name__ == "__main__":
    unittest.main()
