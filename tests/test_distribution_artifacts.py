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
        self.assertIn("python3 -m agentic_os public-release-gate --repo-root . --json", content)
        self.assertIn('python3 -m agentic_os release-install-smoke --source "https://github.com/${{ github.repository }}.git" --ref', content)
        self.assertIn("--fresh-user-smoke --json", content)
        self.assertIn("startsWith(github.ref, 'refs/tags/v')", content)
        self.assertIn("endsWith(github.ref_name, '-public-alpha')", content)
        self.assertIn("${GITHUB_REF_NAME}", content)
        self.assertIn("matrix.os == 'ubuntu-latest'", content)
        self.assertIn("matrix.python-version == '3.13'", content)
        self.assertIn("windows-install:", content)
        self.assertIn("runs-on: windows-latest", content)
        self.assertIn("shell: pwsh", content)
        self.assertIn("python scripts/windows_install_smoke.py --repo-root .", content)
        self.assertIn(r"$env:RUNNER_TEMP\aos-bin", content)

    def test_github_actions_use_node24_compatible_actions(self):
        workflow = self.repo_root / ".github/workflows/test.yml"

        content = workflow.read_text(encoding="utf-8")
        self.assertIn("uses: actions/checkout@v6", content)
        self.assertIn("uses: actions/setup-python@v6", content)
        self.assertNotIn("uses: actions/checkout@v4", content)
        self.assertNotIn("uses: actions/setup-python@v5", content)

    def test_gitignore_blocks_generated_private_outputs(self):
        content = (self.repo_root / ".gitignore").read_text(encoding="utf-8")

        self.assertIn(".agentic-os/", content)
        self.assertIn("AGENTS.md", content)
        self.assertIn("CLAUDE.md", content)
        self.assertIn("GEMINI.md", content)

    def test_readme_documents_standalone_install_and_verification(self):
        content = (self.repo_root / "README.md").read_text(encoding="utf-8")

        self.assertIn("actions/workflows/test.yml/badge.svg", content)
        self.assertIn("img.shields.io/github/v/release/Dai202703/agentic-os-public-alpha", content)
        self.assertIn("img.shields.io/github/license/Dai202703/agentic-os-public-alpha", content)
        self.assertIn("blank-canvas", content)
        self.assertIn("## AOS At A Glance", content)
        self.assertIn("docs/assets/aos-public-alpha-flow.svg", content)
        self.assertLess(content.index("## AOS At A Glance"), content.index("## What It Does"))
        self.assertIn("## Five-Minute Start", content)
        self.assertIn("aos init", content)
        self.assertIn("aos link-project --project-root /tmp/aos-first-project", content)
        self.assertIn("aos compile codex --project-root /tmp/aos-first-project", content)
        self.assertIn("## Choose Your Own Categories", content)
        self.assertIn("docs/install-for-beginners.md", content)
        self.assertIn("AOS does not ship a fixed set of work categories", content)
        self.assertIn("The `--id` you pass to `aos link-project` is your category key", content)
        self.assertIn("letters, numbers, hyphens, or underscores", content)
        self.assertIn("Avoid spaces, slashes, private client names, and secrets", content)
        self.assertIn("## Five Ways To Use AOS", content)
        self.assertIn("### Writer", content)
        self.assertIn("### Researcher", content)
        self.assertIn("### Student", content)
        self.assertIn("### Lawyer", content)
        self.assertIn("### Developer", content)
        self.assertEqual(5, content.count("- Category to create:"))
        self.assertEqual(5, content.count("- Memory to save:"))
        self.assertEqual(5, content.count("- Provider output to compile:"))
        self.assertIn("v0.1.15-public-alpha", content)
        self.assertIn("## Standalone Install", content)
        self.assertIn("git clone https://github.com/Dai202703/agentic-os-public-alpha.git", content)
        self.assertIn("scripts/install.sh", content)
        self.assertIn("scripts/install.ps1", content)
        self.assertIn("macOS / Linux / WSL", content)
        self.assertIn("PowerShell", content)
        self.assertIn(r"powershell -ExecutionPolicy Bypass -File scripts\install.ps1", content)
        self.assertIn("AOS_INSTALL_DIR", content)
        self.assertIn("aos version", content)
        self.assertIn("python3 -m unittest discover -s tests -v", content)
        self.assertIn("aos onboarding-check --project-root . --json", content)
        self.assertIn("aos fresh-user-smoke --repo-root . --json", content)
        self.assertIn("aos release-check --repo-root . --fresh-user-smoke --json", content)
        self.assertIn("aos memory template session --project-id demo", content)
        self.assertIn("re-run `aos compile`", content)
        self.assertIn("aos release-upgrade-smoke --repo-root . --from-ref v0.1.14-public-alpha --to-ref HEAD --json", content)
        self.assertIn("aos public-release-gate --repo-root . --json", content)
        self.assertIn("aos release-install-smoke --source https://github.com/Dai202703/agentic-os-public-alpha.git --ref v0.1.15-public-alpha --expected-tag v0.1.15-public-alpha --fresh-user-smoke --json", content)
        self.assertIn("aos public-audit --repo-root . --tree-only --json", content)
        self.assertIn("aos release-check --repo-root . --skip-release-manifest --json", content)
        self.assertIn("memory add session", content)
        self.assertIn("memory list", content)
        self.assertIn("memory search", content)
        self.assertIn("next_action", content)
        self.assertIn("public-release-manifest.json", content)
        self.assertIn("SHA-256", content)
        self.assertIn("docs/demo.md", content)
        self.assertIn("docs/assets/aos-first-run-demo.svg", content)

    def test_distribution_doc_includes_handoff_verification_gate(self):
        content = (self.repo_root / "docs/distribution.md").read_text(encoding="utf-8")

        self.assertIn("## Handoff Verification Gate", content)
        self.assertIn("Fresh clone test suite passes", content)
        self.assertIn("GitHub Actions test workflow passes", content)
        self.assertIn("aos distribution-check --repo-root . --json", content)
        self.assertIn("aos release-check --repo-root . --json", content)
        self.assertIn("aos release-check --repo-root . --fresh-user-smoke --json", content)
        self.assertIn("aos release-check --repo-root . --upgrade-smoke --from-ref v0.1.14-public-alpha --to-ref HEAD --json", content)
        self.assertIn("aos public-release-gate --repo-root . --json", content)
        self.assertIn("aos release-install-smoke --source https://github.com/Dai202703/agentic-os-public-alpha.git --ref v0.1.15-public-alpha --expected-tag v0.1.15-public-alpha --fresh-user-smoke --json", content)
        self.assertIn("release manifest checksum", content)
        self.assertIn("aos public-audit --repo-root . --json", content)
        self.assertIn("aos onboarding-check --project-root . --json", content)
        self.assertIn("memory add session", content)
        self.assertIn("memory list", content)
        self.assertIn("memory search", content)
        self.assertIn("Final Public Security Gate", content)
        self.assertIn("clean public repository", content)
        self.assertIn("exported snapshot", content)

    def test_public_release_docs_and_policy_files_exist(self):
        required = [
            "docs/assets/aos-public-alpha-flow.svg",
            "docs/assets/aos-first-run-demo.svg",
            "docs/demo.md",
            "docs/memory-workflows.md",
            "docs/install-for-beginners.md",
            "docs/public-release.md",
            "scripts/install.ps1",
            "scripts/windows_install_smoke.py",
            "SECURITY.md",
            "CONTRIBUTING.md",
            "LICENSE",
            "CHANGELOG.md",
        ]

        for relative in required:
            self.assertTrue((self.repo_root / relative).is_file(), relative)

    def test_beginner_install_guide_is_public_and_actionable(self):
        guide = self.repo_root / "docs/install-for-beginners.md"

        self.assertTrue(guide.is_file())
        content = guide.read_text(encoding="utf-8")
        self.assertIn("# Install AOS For Beginners", content)
        self.assertIn("No private data is uploaded", content)
        self.assertIn("macOS, Linux, Windows through WSL, or native Windows PowerShell", content)
        self.assertIn("py -3 --version", content)
        self.assertIn("python --version", content)
        self.assertIn(r"powershell -ExecutionPolicy Bypass -File scripts\install.ps1", content)
        self.assertIn("native Windows PowerShell installer", content)
        self.assertIn("git clone https://github.com/Dai202703/agentic-os-public-alpha.git", content)
        self.assertIn("sh scripts/install.sh", content)
        self.assertIn("scripts/install.ps1", content)
        self.assertIn("aos doctor --summary", content)
        self.assertIn("aos link-project", content)
        self.assertIn("aos compile codex", content)
        self.assertIn("How To Know It Worked", content)
        self.assertIn("Common Problems", content)
        self.assertIn("Windows update", content)
        self.assertIn("-InstallDir", content)
        self.assertIn("re-run `aos compile`", content)

    def test_windows_powershell_installer_is_public_and_safe(self):
        installer = self.repo_root / "scripts/install.ps1"

        self.assertTrue(installer.is_file())
        content = installer.read_text(encoding="utf-8")
        self.assertIn("[CmdletBinding()]", content)
        self.assertIn("AOS_INSTALL_DIR", content)
        self.assertIn("AOS_INSTALL_SKIP_CHECKS", content)
        self.assertIn("aos.cmd", content)
        self.assertIn("aos.ps1", content)
        self.assertIn("readiness_smoke.py", content)
        self.assertIn("AddToUserPath", content)
        self.assertIn("Rollback", content)
        self.assertIn(".aos-install-state.json", content)
        self.assertIn("Move-Item", content)
        self.assertIn("Refusing to replace directory", content)
        self.assertIn("Test-AosLauncherTargets", content)
        self.assertIn("Windows-compatible unittest gate", content)
        self.assertIn("tests.test_release_manifest", content)
        self.assertIn("Remove-Item -LiteralPath $stateFile", content)
        self.assertLess(
            content.index("Recorded backup is missing"),
            content.index("Remove-Item -LiteralPath $ActivePath -Force"),
        )
        self.assertIn("py\" -PrefixArgs @(\"-3\")", content)
        self.assertIn("No private data is uploaded", content)
        self.assertIn("aos init", content)

    def test_windows_install_smoke_script_is_public_and_actionable(self):
        smoke = self.repo_root / "scripts/windows_install_smoke.py"

        self.assertTrue(smoke.is_file())
        content = smoke.read_text(encoding="utf-8")
        self.assertIn("install.ps1", content)
        self.assertIn("aos.cmd", content)
        self.assertIn("aos.ps1", content)
        self.assertIn("-Rollback", content)
        self.assertIn("cmd.exe", content)
        self.assertIn("ExecutionPolicy", content)
        self.assertIn("state_removed", content)

    def test_readme_embeds_visual_quickstart_asset(self):
        asset = self.repo_root / "docs/assets/aos-public-alpha-flow.svg"
        readme = (self.repo_root / "README.md").read_text(encoding="utf-8")

        self.assertTrue(asset.is_file())
        svg = asset.read_text(encoding="utf-8")
        self.assertIn("<svg", svg)
        self.assertIn("<title>", svg)
        self.assertIn("<desc>", svg)
        self.assertIn("Agentic OS", svg)
        self.assertIn("aos init", svg)
        self.assertIn("aos compile codex", svg)
        self.assertIn("AGENTS.md", svg)
        self.assertIn("CLAUDE.md", svg)
        self.assertIn("GEMINI.md", svg)
        self.assertIn("ChatGPT", svg)
        self.assertNotIn("<script", svg)
        self.assertNotIn("<image", svg)
        self.assertNotIn("http://", svg)
        self.assertNotIn("https://", svg)
        self.assertNotIn("data:", svg)
        self.assertNotIn("/Users/", svg)
        self.assertIn("![Agentic OS flow: private local categories and memory compile into provider instruction files](docs/assets/aos-public-alpha-flow.svg)", readme)

    def test_operations_doc_documents_install_update_and_rollback(self):
        operations = self.repo_root / "docs/operations.md"

        self.assertTrue(operations.is_file())
        content = operations.read_text(encoding="utf-8")
        self.assertIn("## Install", content)
        self.assertIn("scripts/install.sh", content)
        self.assertIn("scripts/install.ps1", content)
        self.assertIn("scripts/windows_install_smoke.py", content)
        self.assertIn("AOS_INSTALL_SKIP_CHECKS", content)
        self.assertIn("AOS_INSTALL_LAUNCHER", content)
        self.assertIn("## Update", content)
        self.assertIn("Native Windows update", content)
        self.assertIn("## Rollback", content)
        self.assertIn("scripts/manage_global_aos.py install", content)
        self.assertIn("scripts/manage_global_aos.py update", content)
        self.assertIn("scripts/manage_global_aos.py rollback", content)
        self.assertIn(r"powershell -ExecutionPolicy Bypass -File scripts\install.ps1 -Rollback", content)
        self.assertIn("aos version", content)
        self.assertIn("aos doctor --summary", content)
        self.assertIn("scripts/readiness_smoke.py --launcher bin/aos --json", content)
        self.assertIn("aos fresh-user-smoke --repo-root . --json", content)
        self.assertIn("aos public-release-gate --repo-root . --json", content)
        self.assertIn("aos release-upgrade-smoke --repo-root . --from-ref v0.1.14-public-alpha --to-ref HEAD --json", content)
        self.assertIn("aos release-install-smoke --source https://github.com/Dai202703/agentic-os-public-alpha.git --ref v0.1.15-public-alpha --expected-tag v0.1.15-public-alpha --fresh-user-smoke --json", content)
        self.assertIn("public-release-manifest.json", content)
        self.assertIn("memory add session", content)
        self.assertIn("memory list", content)
        self.assertIn("memory search", content)
        self.assertIn("Final Public Security Gate", content)
        self.assertIn("public repository", content)
        self.assertIn("clean public export", content)

    def test_public_release_doc_documents_version_traceability(self):
        content = (self.repo_root / "docs/public-release.md").read_text(encoding="utf-8")

        self.assertIn("aos version", content)
        self.assertIn("v0.1.15-public-alpha", content)
        self.assertIn("v0.1.14-public-alpha", content)
        self.assertIn("version_consistency", content)
        self.assertIn("release_manifest", content)
        self.assertIn("public-release-gate", content)
        self.assertIn("fresh-user-smoke", content)
        self.assertIn("release-install-smoke", content)
        self.assertIn("release-upgrade-smoke", content)
        self.assertIn("memory add session", content)
        self.assertIn("memory list", content)
        self.assertIn("memory search", content)

    def test_memory_workflows_doc_explains_templates_and_compile_refresh(self):
        content = (self.repo_root / "docs/memory-workflows.md").read_text(encoding="utf-8")

        self.assertIn("# Memory Workflows", content)
        self.assertIn("aos memory template session --project-id demo", content)
        self.assertIn("aos memory template decision --project-id demo", content)
        self.assertIn("re-run `aos compile`", content)
        self.assertIn("Private details stay local", content)

    def test_demo_doc_and_first_run_asset_are_public_safe(self):
        demo_doc = self.repo_root / "docs/demo.md"
        asset = self.repo_root / "docs/assets/aos-first-run-demo.svg"

        self.assertTrue(demo_doc.is_file())
        self.assertTrue(asset.is_file())
        demo_content = demo_doc.read_text(encoding="utf-8")
        svg = asset.read_text(encoding="utf-8")
        self.assertIn("# Agentic OS Demo", demo_content)
        self.assertIn("assets/aos-first-run-demo.svg", demo_content)
        self.assertIn("aos memory template session --project-id first-project", demo_content)
        self.assertIn("<svg", svg)
        self.assertIn("<title>", svg)
        self.assertIn("aos init", svg)
        self.assertIn("aos memory add session", svg)
        self.assertIn("aos compile codex", svg)
        self.assertIn("AGENTS.md", svg)
        self.assertNotIn("<script", svg)
        self.assertNotIn("<image", svg)
        self.assertNotIn("http://", svg)
        self.assertNotIn("https://", svg)
        self.assertNotIn("data:", svg)
        self.assertNotIn("/Users/", svg)

    def test_security_policy_documents_final_public_gate(self):
        content = (self.repo_root / "SECURITY.md").read_text(encoding="utf-8")

        self.assertIn("## Final Public Security Gate", content)
        self.assertIn("aos public-audit --repo-root . --json", content)
        self.assertIn("aos release-check --repo-root . --fresh-user-smoke --upgrade-smoke", content)
        self.assertIn("not public release gates", content)
