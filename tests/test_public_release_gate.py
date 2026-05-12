import io
import json
from types import SimpleNamespace
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agentic_os.cli import main
from agentic_os.public_release_gate import (
    public_release_gate,
    render_public_release_gate_json,
)


class PublicReleaseGateTests(unittest.TestCase):
    def test_public_release_gate_runs_public_audit_and_strict_release_check(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            audit_report = self.audit_report(repo_root, ok=True, history_scanned=True)
            release_report = self.release_report(repo_root, ok=True)

            with patch("agentic_os.public_release_gate.public_audit", return_value=audit_report) as fake_audit:
                with patch("agentic_os.public_release_gate.release_check", return_value=release_report) as fake_release:
                    report = public_release_gate(repo_root, from_ref="v0.1.10-public-alpha")

        self.assertTrue(report.ok)
        self.assertEqual(["public_audit", "release_check"], [step.id for step in report.steps])
        self.assertEqual("PASS", report.steps[0].status)
        self.assertEqual("PASS", report.steps[1].status)
        fake_audit.assert_called_once_with(repo_root.resolve(), include_history=True)
        fake_release.assert_called_once_with(
            repo_root.resolve(),
            repo_root.resolve() / "bin/aos",
            release_manifest_gate=True,
            fresh_user_smoke_gate=True,
            upgrade_smoke=True,
            from_ref="v0.1.10-public-alpha",
            to_ref="HEAD",
        )

    def test_public_release_gate_tree_only_skips_history_audit(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            audit_report = self.audit_report(repo_root, ok=True, history_scanned=False)
            release_report = self.release_report(repo_root, ok=True)

            with patch("agentic_os.public_release_gate.public_audit", return_value=audit_report) as fake_audit:
                with patch("agentic_os.public_release_gate.release_check", return_value=release_report):
                    report = public_release_gate(
                        repo_root,
                        from_ref="v0.1.10-public-alpha",
                        include_history=False,
                    )

        self.assertTrue(report.ok)
        self.assertIn("history not scanned", report.steps[0].message)
        fake_audit.assert_called_once_with(repo_root.resolve(), include_history=False)

    def test_public_release_gate_fails_when_full_history_was_not_scanned(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            audit_report = self.audit_report(repo_root, ok=True, history_scanned=False)
            release_report = self.release_report(repo_root, ok=True)

            with patch("agentic_os.public_release_gate.public_audit", return_value=audit_report):
                with patch("agentic_os.public_release_gate.release_check", return_value=release_report):
                    report = public_release_gate(repo_root, from_ref="v0.1.10-public-alpha")

        self.assertFalse(report.ok)
        self.assertEqual("public_audit", report.failed[0].id)
        self.assertIn("history was not scanned", report.failed[0].message)
        self.assertIn("--tree-only", report.failed[0].next_action)

    def test_public_release_gate_preserves_public_audit_findings(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            finding = SimpleNamespace(
                source="history",
                code="SECRET_PATTERN",
                path="README.md",
                message="Potential secret pattern detected in git history",
                line=7,
                commit="abc123",
            )
            audit_report = self.audit_report(repo_root, ok=False, findings=[finding], history_scanned=True)
            release_report = self.release_report(repo_root, ok=True)

            with patch("agentic_os.public_release_gate.public_audit", return_value=audit_report):
                with patch("agentic_os.public_release_gate.release_check", return_value=release_report):
                    report = public_release_gate(repo_root, from_ref="v0.1.10-public-alpha")

        self.assertFalse(report.ok)
        self.assertEqual("FAIL", report.steps[0].status)
        self.assertIn("1 findings", report.steps[0].message)
        self.assertEqual("Run `aos public-audit --repo-root . --json` and remove reported findings.", report.steps[0].next_action)
        payload = json.loads(render_public_release_gate_json(report))
        self.assertEqual("SECRET_PATTERN", payload["steps"][0]["details"]["findings"][0]["code"])
        self.assertEqual("abc123", payload["steps"][0]["details"]["findings"][0]["commit"])

    def test_public_release_gate_reports_missing_from_ref_inside_release_check(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            audit_report = self.audit_report(repo_root, ok=True, history_scanned=True)
            failed_release = self.release_report(
                repo_root,
                ok=False,
                failed_step=SimpleNamespace(
                    id="release_upgrade_smoke",
                    status="FAIL",
                    message="release-check --upgrade-smoke requires --from-ref.",
                    command=None,
                    path=str(repo_root),
                    stdout_tail=None,
                    stderr_tail=None,
                    next_action=None,
                ),
            )

            with patch("agentic_os.public_release_gate.public_audit", return_value=audit_report):
                with patch("agentic_os.public_release_gate.release_check", return_value=failed_release) as fake_release:
                    report = public_release_gate(repo_root)

        self.assertFalse(report.ok)
        self.assertEqual("release_check", report.failed[0].id)
        self.assertIn("release_upgrade_smoke", report.failed[0].message)
        fake_release.assert_called_once()
        self.assertIsNone(fake_release.call_args.kwargs["from_ref"])

    def test_public_release_gate_cli_outputs_json(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            audit_report = self.audit_report(repo_root, ok=True, history_scanned=True)
            release_report = self.release_report(repo_root, ok=True)
            stdout = io.StringIO()

            with patch("agentic_os.public_release_gate.public_audit", return_value=audit_report):
                with patch("agentic_os.public_release_gate.release_check", return_value=release_report):
                    code = main(
                        [
                            "public-release-gate",
                            "--repo-root",
                            str(repo_root),
                            "--from-ref",
                            "v0.1.10-public-alpha",
                            "--json",
                        ],
                        stdout=stdout,
                    )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(0, code)
        self.assertTrue(payload["ok"])
        self.assertEqual(2, payload["passed_count"])
        self.assertEqual(0, payload["failed_count"])
        self.assertEqual("public_audit", payload["steps"][0]["id"])
        self.assertEqual("release_check", payload["steps"][1]["id"])
        self.assertEqual("version_consistency", payload["steps"][1]["details"]["steps"][0]["id"])

    def test_public_release_gate_cli_preserves_json_when_release_check_raises(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            audit_report = self.audit_report(repo_root, ok=True, history_scanned=True)
            stdout = io.StringIO()

            with patch("agentic_os.public_release_gate.public_audit", return_value=audit_report):
                with patch("agentic_os.public_release_gate.release_check", side_effect=OSError("release root missing")):
                    code = main(
                        [
                            "public-release-gate",
                            "--repo-root",
                            str(repo_root),
                            "--from-ref",
                            "v0.1.10-public-alpha",
                            "--json",
                        ],
                        stdout=stdout,
                    )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(1, code)
        self.assertFalse(payload["ok"])
        self.assertEqual("PASS", payload["steps"][0]["status"])
        self.assertEqual("release_check", payload["steps"][1]["id"])
        self.assertEqual("FAIL", payload["steps"][1]["status"])
        self.assertIn("Release check could not run", payload["steps"][1]["message"])
        self.assertEqual("release root missing", payload["steps"][1]["details"]["error"])

    def audit_report(
        self,
        repo_root: Path,
        *,
        ok: bool,
        history_scanned: bool,
        findings: list[object] | None = None,
    ) -> SimpleNamespace:
        return SimpleNamespace(
            ok=ok,
            repo_root=repo_root.resolve(),
            findings=findings or [],
            history_scanned=history_scanned,
        )

    def release_report(
        self,
        repo_root: Path,
        *,
        ok: bool,
        failed_step: object | None = None,
    ) -> SimpleNamespace:
        passed_steps = [
            SimpleNamespace(
                id="version_consistency",
                status="PASS",
                message="Version metadata is consistent.",
                command=None,
                path=str(repo_root),
                stdout_tail=None,
                stderr_tail=None,
                next_action=None,
            )
        ]
        failed_steps = [failed_step] if failed_step else []
        return SimpleNamespace(
            ok=ok,
            repo_root=repo_root.resolve(),
            steps=passed_steps + failed_steps,
            passed=passed_steps,
            failed=failed_steps,
        )


if __name__ == "__main__":
    unittest.main()
