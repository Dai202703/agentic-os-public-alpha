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
        self.assertIn("public-audit", help_text)
        self.assertIn("public-export", help_text)

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


if __name__ == "__main__":
    unittest.main()
