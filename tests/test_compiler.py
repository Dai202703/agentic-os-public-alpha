import io
import os
import tempfile
import unittest
from pathlib import Path

from agentic_os.bootstrap import init_os
from agentic_os.cli import main
from agentic_os.compiler import compile_provider
from agentic_os.memory import add_decision_memory, add_session_memory
from agentic_os.project import link_project


class CompilerTests(unittest.TestCase):
    def test_compile_codex_writes_agents_file(self):
        with tempfile.TemporaryDirectory() as os_dir, tempfile.TemporaryDirectory() as project_dir:
            os_home = init_os(os_dir)
            (os_home / "core/identity/user.md").write_text("# User Identity\nMy style is pragmatic.\n", encoding="utf-8")
            project_root = Path(project_dir)
            link_project(project_root, "demo", "Demo Project", "product", "dai", ["codex"])

            output_path = compile_provider(os_home, project_root, "codex")

            self.assertEqual(output_path, project_root / "AGENTS.md")
            content = output_path.read_text(encoding="utf-8")
            self.assertIn("Demo Project", content)
            self.assertIn("My style is pragmatic.", content)

    def test_compile_writes_context_fingerprint_metadata(self):
        with tempfile.TemporaryDirectory() as os_dir, tempfile.TemporaryDirectory() as project_dir:
            os_home = init_os(os_dir)
            project_root = Path(project_dir)
            link_project(project_root, "demo", "Demo Project", "product", "dai", ["codex"])

            output_path = compile_provider(os_home, project_root, "codex")

            content = output_path.read_text(encoding="utf-8")
            self.assertRegex(content, r"\nContext-Fingerprint: sha256:[0-9a-f]{64}\n")

    def test_compile_includes_recent_session_and_decision_memory(self):
        with tempfile.TemporaryDirectory() as os_dir, tempfile.TemporaryDirectory() as project_dir:
            os_home = init_os(os_dir)
            project_root = Path(project_dir)
            link_project(project_root, "demo", "Demo Project", "product", "dai", ["codex"])
            add_session_memory(
                os_home,
                "demo",
                "Recent Session",
                "Captured current implementation context.",
                timestamp="2026-05-10 09:30",
            )
            add_decision_memory(
                os_home,
                "demo",
                "Recent Decision",
                "Use recent memory in compiled provider instructions.",
                timestamp="2026-05-10 09:45",
            )

            output_path = compile_provider(os_home, project_root, "codex")

            content = output_path.read_text(encoding="utf-8")
            self.assertIn("## Recent Memory", content)
            self.assertIn("## Recent Sessions", content)
            self.assertIn("Recent Session", content)
            self.assertIn("Captured current implementation context.", content)
            self.assertIn("## Recent Decisions", content)
            self.assertIn("Recent Decision", content)
            self.assertIn("Use recent memory in compiled provider instructions.", content)

    def test_compile_omits_recent_memory_when_no_matching_entries_exist(self):
        with tempfile.TemporaryDirectory() as os_dir, tempfile.TemporaryDirectory() as project_dir:
            os_home = init_os(os_dir)
            project_root = Path(project_dir)
            link_project(project_root, "demo", "Demo Project", "product", "dai", ["codex"])

            output_path = compile_provider(os_home, project_root, "codex")

            content = output_path.read_text(encoding="utf-8")
            self.assertNotIn("## Recent Memory", content)

    def test_compile_includes_decision_memory_without_sessions(self):
        with tempfile.TemporaryDirectory() as os_dir, tempfile.TemporaryDirectory() as project_dir:
            os_home = init_os(os_dir)
            project_root = Path(project_dir)
            link_project(project_root, "demo", "Demo Project", "product", "dai", ["codex"])
            add_decision_memory(
                os_home,
                "demo",
                "Decision Only",
                "Decision rationale should appear without a session section.",
                timestamp="2026-05-10 09:45",
            )

            output_path = compile_provider(os_home, project_root, "codex")

            content = output_path.read_text(encoding="utf-8")
            self.assertIn("## Recent Memory", content)
            self.assertNotIn("## Recent Sessions", content)
            self.assertIn("## Recent Decisions", content)
            self.assertIn("Decision rationale should appear without a session section.", content)

    def test_compile_excludes_recent_memory_from_other_projects(self):
        with tempfile.TemporaryDirectory() as os_dir, tempfile.TemporaryDirectory() as project_dir:
            os_home = init_os(os_dir)
            project_root = Path(project_dir)
            link_project(project_root, "demo", "Demo Project", "product", "dai", ["codex"])
            add_session_memory(
                os_home,
                "other",
                "Other Project Session",
                "This summary belongs to a different project.",
                timestamp="2026-05-10 09:30",
            )
            add_decision_memory(
                os_home,
                "demo",
                "Demo Decision",
                "This rationale belongs to the compiled project.",
                timestamp="2026-05-10 09:45",
            )

            output_path = compile_provider(os_home, project_root, "codex")

            content = output_path.read_text(encoding="utf-8")
            self.assertNotIn("Other Project Session", content)
            self.assertNotIn("This summary belongs to a different project.", content)
            self.assertIn("Demo Decision", content)
            self.assertIn("This rationale belongs to the compiled project.", content)

    def test_compile_sanitizes_recent_memory_title_and_excerpt_without_rewriting_source(self):
        with tempfile.TemporaryDirectory() as os_dir, tempfile.TemporaryDirectory() as project_dir:
            os_home = init_os(os_dir)
            project_root = Path(project_dir)
            link_project(project_root, "demo", "Demo Project", "product", "dai", ["codex"])
            session_path = os_home / "memory/sessions/manual.md"
            session_path.write_text(
                """---
type: "session"
project_id: "demo"
title: "Safe title\\n## Injected Heading\\tTabbed"
timestamp: "2026-05-10 09:30"
---

# Safe title

## Summary

First summary line.
### Nested heading should remain inline.
\tTabbed continuation.

## Decisions

- Not included
""",
                encoding="utf-8",
            )

            output_path = compile_provider(os_home, project_root, "codex")

            content = output_path.read_text(encoding="utf-8")
            recent_block = content.split("## Recent Memory", 1)[1]
            self.assertIn("Safe title ## Injected Heading Tabbed", recent_block)
            self.assertIn("First summary line. ### Nested heading should remain inline. Tabbed continuation.", recent_block)
            self.assertNotIn("\n## Injected Heading", recent_block)
            self.assertNotIn("\t", recent_block)
            self.assertIn('title: "Safe title\\n## Injected Heading\\tTabbed"', session_path.read_text(encoding="utf-8"))

    def test_compile_recent_memory_respects_session_limit(self):
        with tempfile.TemporaryDirectory() as os_dir, tempfile.TemporaryDirectory() as project_dir:
            os_home = init_os(os_dir)
            project_root = Path(project_dir)
            link_project(project_root, "demo", "Demo Project", "product", "dai", ["codex"])
            (project_root / ".agentic-os/project.yaml").write_text(
                """id: "demo"
name: "Demo Project"
contexts:
  - core/identity
memory:
  include_recent_sessions: 1
  include_recent_decisions: 0
providers:
  - "codex"
""",
                encoding="utf-8",
            )
            add_session_memory(
                os_home,
                "demo",
                "Older Session",
                "Previous implementation context.",
                timestamp="2026-05-10 09:00",
            )
            add_session_memory(
                os_home,
                "demo",
                "Newest Session",
                "Latest implementation context.",
                timestamp="2026-05-10 10:00",
            )

            output_path = compile_provider(os_home, project_root, "codex")

            content = output_path.read_text(encoding="utf-8")
            self.assertIn("Newest Session", content)
            self.assertNotIn("Older Session", content)

    def test_compile_chatgpt_writes_instruction_bundle_under_agentic_os_dir(self):
        with tempfile.TemporaryDirectory() as os_dir, tempfile.TemporaryDirectory() as project_dir:
            os_home = init_os(os_dir)
            project_root = Path(project_dir)
            link_project(project_root, "demo", "Demo Project", "product", "dai", ["chatgpt"])

            output_path = compile_provider(os_home, project_root, "chatgpt")

            self.assertEqual(output_path, project_root / ".agentic-os/chatgpt-project-instructions.md")
            self.assertTrue(output_path.is_file())

    def test_compile_rejects_provider_not_declared_for_project(self):
        with tempfile.TemporaryDirectory() as os_dir, tempfile.TemporaryDirectory() as project_dir:
            os_home = init_os(os_dir)
            project_root = Path(project_dir)
            link_project(project_root, "demo", "Demo Project", "product", "dai", ["codex"])

            with self.assertRaises(ValueError):
                compile_provider(os_home, project_root, "chatgpt")

            self.assertFalse((project_root / ".agentic-os/chatgpt-project-instructions.md").exists())

    def test_compile_rejects_context_outside_os_home(self):
        with tempfile.TemporaryDirectory() as base_dir:
            base_path = Path(base_dir)
            os_home = init_os(base_path / "os")
            project_root = base_path / "project"
            link_project(project_root, "demo", "Demo Project", "product", "dai", ["codex"])
            (base_path / "secret.md").write_text("private data\n", encoding="utf-8")
            (project_root / ".agentic-os/project.yaml").write_text(
                """id: "demo"
name: "Demo Project"
contexts:
  - ../secret.md
providers:
  - "codex"
""",
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                compile_provider(os_home, project_root, "codex")

    def test_compile_rejects_missing_context(self):
        with tempfile.TemporaryDirectory() as os_dir, tempfile.TemporaryDirectory() as project_dir:
            os_home = init_os(os_dir)
            project_root = Path(project_dir)
            link_project(project_root, "demo", "Demo Project", "product", "dai", ["codex"])
            (project_root / ".agentic-os/project.yaml").write_text(
                """id: "demo"
name: "Demo Project"
contexts:
  - core/missing
providers:
  - "codex"
""",
                encoding="utf-8",
            )

            with self.assertRaises(FileNotFoundError):
                compile_provider(os_home, project_root, "codex")

    def test_compile_command_reports_error_for_context_outside_os_home(self):
        with tempfile.TemporaryDirectory() as base_dir:
            base_path = Path(base_dir)
            os_home = init_os(base_path / "os")
            project_root = base_path / "project"
            link_project(project_root, "demo", "Demo Project", "product", "dai", ["codex"])
            (base_path / "secret.md").write_text("private data\n", encoding="utf-8")
            (project_root / ".agentic-os/project.yaml").write_text(
                """id: "demo"
name: "Demo Project"
contexts:
  - ../secret.md
providers:
  - "codex"
""",
                encoding="utf-8",
            )
            stderr = io.StringIO()

            exit_code = main(
                ["--os-home", str(os_home), "compile", "codex", "--project-root", str(project_root)],
                stderr=stderr,
            )

            self.assertEqual(exit_code, 1)
            self.assertIn("Error:", stderr.getvalue())

    def test_compile_rejects_symlinked_markdown_context_outside_os_home(self):
        with tempfile.TemporaryDirectory() as base_dir:
            base_path = Path(base_dir)
            os_home = init_os(base_path / "os")
            project_root = base_path / "project"
            secret_path = base_path / "secret.md"
            secret_path.write_text("private data\n", encoding="utf-8")
            symlink_path = os_home / "core/identity/linked-secret.md"
            try:
                symlink_path.symlink_to(secret_path)
            except (NotImplementedError, OSError) as error:
                self.skipTest(f"Symlink creation is unsupported: {error}")
            link_project(project_root, "demo", "Demo Project", "product", "dai", ["codex"])

            with self.assertRaises(ValueError):
                compile_provider(os_home, project_root, "codex")

    def test_compile_rejects_hardlinked_markdown_context_outside_os_home(self):
        with tempfile.TemporaryDirectory() as base_dir:
            base_path = Path(base_dir)
            os_home = init_os(base_path / "os")
            project_root = base_path / "project"
            outside_file = base_path / "outside-context.md"
            outside_file.write_text("private context data\n", encoding="utf-8")
            hardlink_path = os_home / "core/identity/hardlinked-context.md"
            try:
                os.link(outside_file, hardlink_path)
            except (NotImplementedError, OSError) as error:
                self.skipTest(f"Hardlink creation is unsupported: {error}")
            link_project(project_root, "demo", "Demo Project", "product", "dai", ["codex"])

            with self.assertRaises(ValueError):
                compile_provider(os_home, project_root, "codex")

            self.assertFalse((project_root / "AGENTS.md").exists())

    def test_compile_excludes_hardlinked_recent_memory_outside_os_home(self):
        with tempfile.TemporaryDirectory() as base_dir:
            base_path = Path(base_dir)
            os_home = init_os(base_path / "os")
            project_root = base_path / "project"
            outside_file = base_path / "outside-memory.md"
            outside_file.write_text(
                """---
type: "session"
project_id: "demo"
title: "Outside Memory"
timestamp: "2026-05-10 09:30"
---

# Outside Memory

## Summary

private memory data
""",
                encoding="utf-8",
            )
            hardlink_path = os_home / "memory/sessions/hardlinked-memory.md"
            try:
                os.link(outside_file, hardlink_path)
            except (NotImplementedError, OSError) as error:
                self.skipTest(f"Hardlink creation is unsupported: {error}")
            link_project(project_root, "demo", "Demo Project", "product", "dai", ["codex"])

            output_path = compile_provider(os_home, project_root, "codex")

            content = output_path.read_text(encoding="utf-8")
            self.assertNotIn("Outside Memory", content)
            self.assertNotIn("private memory data", content)

    def test_compile_rejects_symlinked_provider_template_outside_os_home(self):
        with tempfile.TemporaryDirectory() as base_dir:
            base_path = Path(base_dir)
            os_home = init_os(base_path / "os")
            project_root = base_path / "project"
            outside_template = base_path / "outside-template.md"
            outside_template.write_text("private template data\n", encoding="utf-8")
            template_path = os_home / "providers/codex/AGENTS.template.md"
            template_path.unlink()
            try:
                template_path.symlink_to(outside_template)
            except (NotImplementedError, OSError) as error:
                self.skipTest(f"Symlink creation is unsupported: {error}")
            link_project(project_root, "demo", "Demo Project", "product", "dai", ["codex"])

            with self.assertRaises(ValueError):
                compile_provider(os_home, project_root, "codex")

            self.assertFalse((project_root / "AGENTS.md").exists())

    def test_compile_rejects_hardlinked_provider_template_outside_os_home(self):
        with tempfile.TemporaryDirectory() as base_dir:
            base_path = Path(base_dir)
            os_home = init_os(base_path / "os")
            project_root = base_path / "project"
            outside_template = base_path / "outside-template.md"
            outside_template.write_text("private template data\n", encoding="utf-8")
            template_path = os_home / "providers/codex/AGENTS.template.md"
            template_path.unlink()
            try:
                os.link(outside_template, template_path)
            except (NotImplementedError, OSError) as error:
                self.skipTest(f"Hardlink creation is unsupported: {error}")
            link_project(project_root, "demo", "Demo Project", "product", "dai", ["codex"])

            with self.assertRaises(ValueError):
                compile_provider(os_home, project_root, "codex")

            self.assertFalse((project_root / "AGENTS.md").exists())

    def test_compile_rejects_symlinked_project_config_outside_project(self):
        with tempfile.TemporaryDirectory() as base_dir:
            base_path = Path(base_dir)
            os_home = init_os(base_path / "os")
            project_root = base_path / "project"
            link_project(project_root, "demo", "Demo Project", "product", "dai", ["chatgpt"])
            outside_config = base_path / "outside-project.yaml"
            outside_config.write_text(
                'id: "demo"\nname: "Demo Project"\ncontexts:\n  - core/identity\nproviders:\n  - "chatgpt"\n',
                encoding="utf-8",
            )
            config_path = project_root / ".agentic-os/project.yaml"
            config_path.unlink()
            try:
                config_path.symlink_to(outside_config)
            except (NotImplementedError, OSError) as error:
                self.skipTest(f"Symlink creation is unsupported: {error}")

            with self.assertRaises(ValueError):
                compile_provider(os_home, project_root, "chatgpt")

            self.assertFalse((project_root / ".agentic-os/chatgpt-project-instructions.md").exists())

    def test_compile_rejects_symlinked_project_root_without_writing_target(self):
        with tempfile.TemporaryDirectory() as base_dir:
            base_path = Path(base_dir)
            os_home = init_os(base_path / "os")
            real_project_root = base_path / "real-project"
            project_root = base_path / "project-link"
            link_project(real_project_root, "demo", "Demo Project", "product", "dai", ["codex"])
            try:
                project_root.symlink_to(real_project_root, target_is_directory=True)
            except (NotImplementedError, OSError) as error:
                self.skipTest(f"Symlink creation is unsupported: {error}")

            with self.assertRaises(ValueError):
                compile_provider(os_home, project_root, "codex")

            self.assertFalse((real_project_root / "AGENTS.md").exists())

    def test_compile_rejects_symlink_component_before_parent_segment_without_writing_target(self):
        with tempfile.TemporaryDirectory() as base_dir:
            base_path = Path(base_dir)
            os_home = init_os(base_path / "os")
            real_project_root = base_path / "real-project"
            project_link = base_path / "project-link"
            link_project(real_project_root, "demo", "Demo Project", "product", "dai", ["codex"])
            (real_project_root / "nested").mkdir()
            try:
                project_link.symlink_to(real_project_root, target_is_directory=True)
            except (NotImplementedError, OSError) as error:
                self.skipTest(f"Symlink creation is unsupported: {error}")

            with self.assertRaises(ValueError):
                compile_provider(os_home, project_link / "nested" / "..", "codex")

            self.assertFalse((real_project_root / "AGENTS.md").exists())

    def test_compile_rejects_symlinked_existing_output_file(self):
        with tempfile.TemporaryDirectory() as base_dir:
            base_path = Path(base_dir)
            os_home = init_os(base_path / "os")
            project_root = base_path / "project"
            outside_file = base_path / "outside-agents.md"
            link_project(project_root, "demo", "Demo Project", "product", "dai", ["codex"])
            try:
                (project_root / "AGENTS.md").symlink_to(outside_file)
            except (NotImplementedError, OSError) as error:
                self.skipTest(f"Symlink creation is unsupported: {error}")

            with self.assertRaises(ValueError):
                compile_provider(os_home, project_root, "codex")

            self.assertFalse(outside_file.exists())

    def test_compile_rejects_hardlinked_existing_output_file_without_writing_outside(self):
        with tempfile.TemporaryDirectory() as base_dir:
            base_path = Path(base_dir)
            os_home = init_os(base_path / "os")
            project_root = base_path / "project"
            outside_file = base_path / "outside-agents.md"
            link_project(project_root, "demo", "Demo Project", "product", "dai", ["codex"])
            outside_file.write_text("outside agents\n", encoding="utf-8")
            try:
                os.link(outside_file, project_root / "AGENTS.md")
            except (NotImplementedError, OSError) as error:
                self.skipTest(f"Hardlink creation is unsupported: {error}")

            with self.assertRaises(ValueError):
                compile_provider(os_home, project_root, "codex")

            self.assertEqual(outside_file.read_text(encoding="utf-8"), "outside agents\n")
