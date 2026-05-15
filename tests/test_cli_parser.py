import io
import unittest

from agentic_os.cli import build_parser, main


class CliParserTests(unittest.TestCase):
    def test_parser_exposes_initial_commands(self):
        parser = build_parser()
        help_text = parser.format_help()

        self.assertIn("init", help_text)
        self.assertIn("doctor", help_text)
        self.assertIn("distribution-check", help_text)
        self.assertIn("release-check", help_text)
        self.assertIn("fresh-user-smoke", help_text)
        self.assertIn("release-upgrade-smoke", help_text)
        self.assertIn("release-install-smoke", help_text)
        self.assertIn("public-audit", help_text)
        self.assertIn("public-export", help_text)
        self.assertIn("public-release-gate", help_text)
        self.assertIn("version", help_text)

    def test_os_home_global_option_is_available(self):
        parser = build_parser()
        args = parser.parse_args(["--os-home", "/tmp/aos-test", "doctor"])

        self.assertEqual(args.os_home, "/tmp/aos-test")
        self.assertEqual(args.command, "doctor")

    def test_main_returns_parse_error_code_for_unknown_command(self):
        stderr = io.StringIO()

        status = main(["unknown"], stderr=stderr)

        self.assertEqual(status, 2)
        self.assertIn("invalid choice", stderr.getvalue())

    def test_doctor_accepts_project_root(self):
        parser = build_parser()

        args = parser.parse_args(["doctor", "--project-root", "/tmp/project"])

        self.assertEqual(args.command, "doctor")
        self.assertEqual(args.project_root, "/tmp/project")

    def test_release_commands_include_operator_help_text(self):
        parser = build_parser()
        subparsers_action = next(action for action in parser._actions if getattr(action, "dest", None) == "command")
        release_check_help = _normalize_help(subparsers_action.choices["release-check"].format_help())
        release_install_help = _normalize_help(subparsers_action.choices["release-install-smoke"].format_help())
        public_gate_help = _normalize_help(subparsers_action.choices["public-release-gate"].format_help())

        self.assertIn("Previous release ref", release_check_help)
        self.assertIn("Run the isolated first-user", release_check_help)
        self.assertIn("full isolated first-user smoke", release_install_help)
        self.assertIn("--fresh-user-smoke", release_install_help)
        self.assertIn("latest older same-channel tag", public_gate_help)
        self.assertIn("--release-install-fresh-user-smoke", public_gate_help)

    def test_memory_template_command_is_available(self):
        parser = build_parser()
        args = parser.parse_args(["memory", "template", "session", "--project-id", "demo"])

        self.assertEqual(args.command, "memory")
        self.assertEqual(args.memory_command, "template")
        self.assertEqual(args.memory_template_type, "session")
        self.assertEqual(args.project_id, "demo")


def _normalize_help(help_text: str) -> str:
    return " ".join(help_text.split())


if __name__ == "__main__":
    unittest.main()
