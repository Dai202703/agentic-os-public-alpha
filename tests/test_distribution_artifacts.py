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
        self.assertIn("python3 -m agentic_os release-check --repo-root . --skip-release-manifest --json", content)
        self.assertIn("python3 -m agentic_os public-audit --repo-root . --json", content)
        self.assertIn("github.repository", content)
        self.assertIn("Dai202703/agentic-os-public-alpha", content)
        self.assertIn("python3 -m agentic_os public-audit --repo-root . --tree-only --json", content)
        self.assertIn("python3 -m agentic_os fresh-user-smoke --repo-root . --json", content)

    def test_github_actions_use_node24_compatible_actions(self):
        workflow = self.repo_root / ".github/workflows/test.yml"

        content = workflow.read_text(encoding="utf-8")
        self.assertIn("uses: actions/checkout@v6", content)
        self.assertIn("uses: actions/setup-python@v6", content)
        self.assertNotIn("uses: actions/checkout@v4", content)
        self.assertNotIn("uses: actions/setup-python@v5", content)

    def test_readme_documents_standalone_install_and_verification(self):
        content = (self.repo_root / "README.md").read_text(encoding="utf-8")

        self.assertIn("## Standalone Install", content)
        self.assertIn("git clone https://github.com/Dai202703/agentic-os-public-alpha.git", content)
        self.assertIn("scripts/install.sh", content)
        self.assertIn("AOS_INSTALL_DIR", content)
        self.assertIn("aos version", content)
        self.assertIn("python3 -m unittest discover -s tests -v", content)
        self.assertIn("aos onboarding-check --project-root . --json", content)
        self.assertIn("aos fresh-user-smoke --repo-root . --json", content)
        self.assertIn("aos release-check --repo-root . --fresh-user-smoke --json", content)
        self.assertIn("aos release-upgrade-smoke --repo-root . --from-ref v0.1.9-public-alpha --to-ref HEAD --json", content)
        self.assertIn("aos public-audit --repo-root . --tree-only --json", content)
        self.assertIn("aos release-check --repo-root . --skip-release-manifest --json", content)
        self.assertIn("memory add session", content)
        self.assertIn("memory list", content)
        self.assertIn("memory search", content)
        self.assertIn("next_action", content)
        self.assertIn("public-release-manifest.json", content)
        self.assertIn("SHA-256", content)

    def test_distribution_doc_includes_handoff_verification_gate(self):
        content = (self.repo_root / "docs/distribution.md").read_text(encoding="utf-8")

        self.assertIn("## Handoff Verification Gate", content)
        self.assertIn("Fresh clone test suite passes", content)
        self.assertIn("GitHub Actions test workflow passes", content)
        self.assertIn("aos distribution-check --repo-root . --json", content)
        self.assertIn("aos release-check --repo-root . --json", content)
        self.assertIn("aos release-check --repo-root . --fresh-user-smoke --json", content)
        self.assertIn("aos release-check --repo-root . --upgrade-smoke --from-ref v0.1.9-public-alpha --to-ref HEAD --json", content)
        self.assertIn("release manifest checksum", content)
        self.assertIn("aos public-audit --repo-root . --json", content)
        self.assertIn("aos onboarding-check --project-root . --json", content)
        self.assertIn("memory add session", content)
        self.assertIn("memory list", content)
        self.assertIn("memory search", content)

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
        self.assertIn("AOS_INSTALL_LAUNCHER", content)
        self.assertIn("## Update", content)
        self.assertIn("## Rollback", content)
        self.assertIn("scripts/manage_global_aos.py install", content)
        self.assertIn("scripts/manage_global_aos.py update", content)
        self.assertIn("scripts/manage_global_aos.py rollback", content)
        self.assertIn("aos version", content)
        self.assertIn("aos doctor --summary", content)
        self.assertIn("scripts/readiness_smoke.py --launcher bin/aos --json", content)
        self.assertIn("aos fresh-user-smoke --repo-root . --json", content)
        self.assertIn("aos release-upgrade-smoke --repo-root . --from-ref v0.1.9-public-alpha --to-ref HEAD --json", content)
        self.assertIn("public-release-manifest.json", content)
        self.assertIn("memory add session", content)
        self.assertIn("memory list", content)
        self.assertIn("memory search", content)

    def test_public_release_doc_documents_version_traceability(self):
        content = (self.repo_root / "docs/public-release.md").read_text(encoding="utf-8")

        self.assertIn("aos version", content)
        self.assertIn("v0.1.10-public-alpha", content)
        self.assertIn("v0.1.9-public-alpha", content)
        self.assertIn("version_consistency", content)
        self.assertIn("release_manifest", content)
        self.assertIn("fresh-user-smoke", content)
        self.assertIn("release-upgrade-smoke", content)
        self.assertIn("memory add session", content)
        self.assertIn("memory list", content)
        self.assertIn("memory search", content)
