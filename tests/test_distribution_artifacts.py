import unittest
from pathlib import Path


class DistributionArtifactsTests(unittest.TestCase):
    def setUp(self):
        self.repo_root = Path(__file__).resolve().parents[1]

    def test_github_actions_runs_standalone_unittest_suite(self):
        workflow = self.repo_root / ".github/workflows/test.yml"

        self.assertTrue(workflow.is_file())
        content = workflow.read_text(encoding="utf-8")
        self.assertIn("PYTHONPATH: src", content)
        self.assertIn("python3 -m unittest discover -s tests -v", content)
        self.assertIn("python3 -m agentic_os distribution-check --repo-root . --json", content)
        self.assertIn("python3 -m agentic_os release-check --repo-root . --json", content)
        self.assertIn("python3 -m agentic_os public-audit --repo-root . --json", content)

    def test_readme_documents_standalone_install_and_verification(self):
        content = (self.repo_root / "README.md").read_text(encoding="utf-8")

        self.assertIn("## Standalone Install", content)
        self.assertIn("git clone https://github.com/Dai202703/agentic-os-public-alpha.git", content)
        self.assertIn("scripts/install.sh", content)
        self.assertIn("AOS_INSTALL_DIR", content)
        self.assertIn("python3 -m unittest discover -s tests -v", content)
        self.assertIn("aos onboarding-check --project-root . --json", content)

    def test_distribution_doc_includes_handoff_verification_gate(self):
        content = (self.repo_root / "docs/distribution.md").read_text(encoding="utf-8")

        self.assertIn("## Handoff Verification Gate", content)
        self.assertIn("Fresh clone test suite passes", content)
        self.assertIn("GitHub Actions test workflow passes", content)
        self.assertIn("aos distribution-check --repo-root . --json", content)
        self.assertIn("aos release-check --repo-root . --json", content)
        self.assertIn("aos public-audit --repo-root . --json", content)
        self.assertIn("aos onboarding-check --project-root . --json", content)

    def test_public_release_docs_and_policy_files_exist(self):
        required = [
            "docs/public-release.md",
            "SECURITY.md",
            "CONTRIBUTING.md",
            "LICENSE",
            "CHANGELOG.md",
        ]

        for relative in required:
            self.assertTrue((self.repo_root / relative).is_file(), relative)

    def test_operations_doc_documents_install_update_and_rollback(self):
        operations = self.repo_root / "docs/operations.md"

        self.assertTrue(operations.is_file())
        content = operations.read_text(encoding="utf-8")
        self.assertIn("## Install", content)
        self.assertIn("scripts/install.sh", content)
        self.assertIn("AOS_INSTALL_SKIP_CHECKS", content)
        self.assertIn("## Update", content)
        self.assertIn("## Rollback", content)
        self.assertIn("scripts/manage_global_aos.py install", content)
        self.assertIn("scripts/manage_global_aos.py update", content)
        self.assertIn("scripts/manage_global_aos.py rollback", content)
        self.assertIn("aos doctor --summary", content)
        self.assertIn("scripts/readiness_smoke.py --launcher bin/aos --json", content)
