import io
import os
import shutil
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from agentic_os.bootstrap import init_os
from agentic_os.cli import main
from agentic_os.memory import (
    add_decision_memory,
    add_session_memory,
    render_decision_memory_template,
    render_session_memory_template,
    update_project_state,
)


class MemoryTests(unittest.TestCase):
    def test_add_decision_memory_writes_decision_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os_home = init_os(temp_dir)

            rationale = """  We chose path-checked writes because:

- Memory files are durable project records.
- Reviewers need rationale structure preserved.
  - Nested bullets should keep indentation.

Follow-up remains visible.  """

            decision_path = add_decision_memory(
                os_home,
                project_id="demo",
                title="  Choose\n Security\tFirst  ",
                rationale=rationale,
                timestamp="2026-05-10 09:45",
            )

            self.assertTrue(decision_path.is_file())
            self.assertEqual("2026-05-10-0945-choose-security-first.md", decision_path.name)
            content = decision_path.read_text(encoding="utf-8")
            self.assertTrue(content.startswith("---\n"))
            self.assertIn('type: "decision"', content)
            self.assertIn('project_id: "demo"', content)
            self.assertIn('title: "Choose Security First"', content)
            self.assertIn('timestamp: "2026-05-10 09:45"', content)
            self.assertIn("# Choose Security First", content)
            self.assertIn("**Project:** demo", content)
            self.assertIn("**Timestamp:** 2026-05-10 09:45", content)
            self.assertIn(
                "\n".join(
                    [
                        "## Rationale",
                        "",
                        "We chose path-checked writes because:",
                        "",
                        "- Memory files are durable project records.",
                        "- Reviewers need rationale structure preserved.",
                        "  - Nested bullets should keep indentation.",
                        "",
                        "Follow-up remains visible.",
                    ]
                ),
                content,
            )

            project_state = os_home / "memory/project-state/demo.md"
            self.assertTrue(project_state.is_file())
            self.assertIn(
                "2026-05-10 09:45: Choose Security First",
                project_state.read_text(encoding="utf-8"),
            )

    def test_add_decision_memory_rejects_empty_rationale(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os_home = init_os(temp_dir)

            with self.assertRaises(ValueError):
                add_decision_memory(
                    os_home,
                    project_id="demo",
                    title="Choose Security First",
                    rationale="\n\t",
                    timestamp="2026-05-10 09:45",
                )

    def test_add_session_memory_writes_session_file_and_project_state(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os_home = init_os(temp_dir)

            session_path = add_session_memory(
                os_home,
                project_id="demo",
                title="Plan Agentic OS",
                summary="Created the core MVP implementation plan.",
                next_actions=["Review plan", "Start Task 1"],
                timestamp="2026-05-10 09:30",
            )

            self.assertTrue(session_path.is_file())
            content = session_path.read_text(encoding="utf-8")
            self.assertIn("# Plan Agentic OS", content)
            self.assertIn("Created the core MVP implementation plan.", content)
            self.assertIn("- Review plan", content)

            project_state = os_home / "memory/project-state/demo.md"
            self.assertTrue(project_state.is_file())
            self.assertIn("Plan Agentic OS", project_state.read_text(encoding="utf-8"))

    def test_add_session_memory_writes_metadata_tags_decisions_and_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os_home = init_os(temp_dir)

            session_path = add_session_memory(
                os_home,
                project_id="demo",
                title="Capture Session Metadata",
                summary="Captured richer session context.",
                next_actions=["Review captured memory"],
                timestamp="2026-05-10 09:30",
                tags=["hardening", "memory"],
                decisions=["Store session metadata as front matter"],
                artifacts=["agentic-os/src/agentic_os/memory.py"],
            )

            content = session_path.read_text(encoding="utf-8")
            self.assertTrue(content.startswith("---\n"))
            self.assertIn('type: "session"', content)
            self.assertIn('project_id: "demo"', content)
            self.assertIn('title: "Capture Session Metadata"', content)
            self.assertIn('timestamp: "2026-05-10 09:30"', content)
            self.assertIn('tags:\n  - "hardening"\n  - "memory"', content)
            self.assertIn("## Summary\n\nCaptured richer session context.", content)
            self.assertIn("## Decisions\n\n- Store session metadata as front matter", content)
            self.assertIn("## Artifacts\n\n- agentic-os/src/agentic_os/memory.py", content)
            self.assertIn("## Next Actions\n\n- Review captured memory", content)

    def test_add_session_memory_writes_empty_tags_as_front_matter_list_block(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os_home = init_os(temp_dir)

            session_path = add_session_memory(
                os_home,
                project_id="demo",
                title="No Tags",
                summary="Captured session without tags.",
                timestamp="2026-05-10 09:30",
            )

            content = session_path.read_text(encoding="utf-8")
            front_matter = content.split("---\n", 2)[1]
            self.assertIn('timestamp: "2026-05-10 09:30"\ntags:\n', front_matter)
            self.assertNotIn("tags: []", front_matter)

    def test_add_session_memory_normalizes_metadata_and_list_values(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os_home = init_os(temp_dir)

            session_path = add_session_memory(
                os_home,
                project_id="demo",
                title="  Capture\n Session\tMetadata  ",
                summary="  Captured\n richer\t session context.  ",
                next_actions=["  Review\n captured memory  ", " \n\t "],
                timestamp="2026-05-10 09:30",
                tags=[" hardening\n memory ", " \t "],
                decisions=[" Store\n metadata\tas front matter "],
                artifacts=[" agentic-os/src/agentic_os/memory.py\n line 1 "],
            )

            self.assertEqual("2026-05-10-0930-capture-session-metadata.md", session_path.name)
            content = session_path.read_text(encoding="utf-8")
            self.assertIn('title: "Capture Session Metadata"', content)
            self.assertIn("# Capture Session Metadata", content)
            self.assertIn("## Summary\n\nCaptured richer session context.", content)
            self.assertIn('tags:\n  - "hardening memory"', content)
            self.assertNotIn(" \t ", content)
            self.assertNotIn("-  ", content)
            self.assertIn("## Decisions\n\n- Store metadata as front matter", content)
            self.assertIn("## Artifacts\n\n- agentic-os/src/agentic_os/memory.py line 1", content)
            self.assertIn("## Next Actions\n\n- Review captured memory", content)

            project_state = os_home / "memory/project-state/demo.md"
            self.assertIn(
                "2026-05-10 09:30: Capture Session Metadata",
                project_state.read_text(encoding="utf-8"),
            )

    def test_add_session_memory_rejects_empty_title(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os_home = init_os(temp_dir)

            with self.assertRaises(ValueError):
                add_session_memory(
                    os_home,
                    project_id="demo",
                    title="  ",
                    summary="Summary is present.",
                    timestamp="2026-05-10 09:30",
                )

    def test_add_session_memory_rejects_empty_summary(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os_home = init_os(temp_dir)

            with self.assertRaises(ValueError):
                add_session_memory(
                    os_home,
                    project_id="demo",
                    title="Summary Validation",
                    summary="\n\t",
                    timestamp="2026-05-10 09:30",
                )

    def test_update_project_state_rejects_path_unsafe_project_id(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os_home = init_os(temp_dir)
            escaped_name = f"escaped-{os_home.name}"
            outside_path = os_home.parent / f"{escaped_name}.md"

            with self.assertRaises(ValueError):
                update_project_state(
                    os_home,
                    f"../../../{escaped_name}",
                    "Title",
                    datetime(2026, 5, 10, 9, 30),
                )

            self.assertFalse(outside_path.exists())

    def test_add_session_memory_rejects_path_unsafe_project_id(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os_home = init_os(temp_dir)

            with self.assertRaises(ValueError):
                add_session_memory(
                    os_home,
                    project_id="../../../escaped",
                    title="Unsafe Project",
                    summary="This should not write outside project state.",
                    timestamp="2026-05-10 09:30",
                )

    def test_add_session_memory_rejects_symlinked_sessions_directory_outside_os_home(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os_home = init_os(temp_dir)
            outside_dir = Path(temp_dir) / "outside-sessions"
            outside_dir.mkdir()
            shutil.rmtree(os_home / "memory/sessions")
            try:
                (os_home / "memory/sessions").symlink_to(outside_dir, target_is_directory=True)
            except (NotImplementedError, OSError) as error:
                self.skipTest(f"Symlink creation is unsupported: {error}")

            with self.assertRaises(ValueError):
                add_session_memory(
                    os_home,
                    project_id="demo",
                    title="Unsafe Session",
                    summary="This should not write outside sessions.",
                    timestamp="2026-05-10 09:30",
                )

            self.assertFalse((outside_dir / "2026-05-10-0930-unsafe-session.md").exists())

    def test_render_session_memory_template_outputs_copy_paste_command(self):
        template = render_session_memory_template("demo")

        self.assertIn("aos memory add session --project-id demo", template)
        self.assertIn('--title "Session title"', template)
        self.assertIn('--summary "What changed, why it matters, and what should persist."', template)
        self.assertIn('--tag "handoff"', template)
        self.assertIn('--decision "Key decision made during the session."', template)
        self.assertIn('--artifact "path/or/link-to-important-output"', template)
        self.assertIn('--next-action "Concrete next step."', template)
        self.assertIn("re-run `aos compile`", template)

    def test_render_decision_memory_template_outputs_copy_paste_command(self):
        template = render_decision_memory_template("demo")

        self.assertIn("aos memory add decision --project-id demo", template)
        self.assertIn('--title "Decision title"', template)
        self.assertIn('--rationale "Context, options considered, and why this path was chosen."', template)

    def test_memory_template_rejects_unsafe_project_id(self):
        with self.assertRaises(ValueError):
            render_session_memory_template("../private")

        with self.assertRaises(ValueError):
            render_decision_memory_template("../private")

    def test_memory_template_cli_outputs_session_template(self):
        stdout = io.StringIO()

        status = main(["memory", "template", "session", "--project-id", "demo"], stdout=stdout)

        self.assertEqual(0, status)
        self.assertIn("aos memory add session --project-id demo", stdout.getvalue())

    def test_memory_template_cli_outputs_decision_template(self):
        stdout = io.StringIO()

        status = main(["memory", "template", "decision", "--project-id", "demo"], stdout=stdout)

        self.assertEqual(0, status)
        self.assertIn("aos memory add decision --project-id demo", stdout.getvalue())

    def test_add_session_memory_rejects_symlinked_session_file_outside_os_home(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os_home = init_os(temp_dir)
            outside_file = Path(temp_dir) / "outside-session.md"
            session_link = os_home / "memory/sessions/2026-05-10-0930-unsafe-session.md"
            try:
                session_link.symlink_to(outside_file)
            except (NotImplementedError, OSError) as error:
                self.skipTest(f"Symlink creation is unsupported: {error}")

            with self.assertRaises(ValueError):
                add_session_memory(
                    os_home,
                    project_id="demo",
                    title="Unsafe Session",
                    summary="This should not write through the session symlink.",
                    timestamp="2026-05-10 09:30",
                )

            self.assertFalse(outside_file.exists())

    def test_add_decision_memory_rejects_symlinked_decisions_directory_outside_os_home(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os_home = init_os(temp_dir)
            outside_dir = Path(temp_dir) / "outside-decisions"
            outside_dir.mkdir()
            shutil.rmtree(os_home / "memory/decisions")
            try:
                (os_home / "memory/decisions").symlink_to(outside_dir, target_is_directory=True)
            except (NotImplementedError, OSError) as error:
                self.skipTest(f"Symlink creation is unsupported: {error}")

            with self.assertRaises(ValueError):
                add_decision_memory(
                    os_home,
                    project_id="demo",
                    title="Unsafe Decision",
                    rationale="This should not write outside decisions.",
                    timestamp="2026-05-10 09:45",
                )

            self.assertFalse((outside_dir / "2026-05-10-0945-unsafe-decision.md").exists())

    def test_add_decision_memory_rejects_symlinked_decision_file_outside_os_home(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os_home = init_os(temp_dir)
            outside_file = Path(temp_dir) / "outside-decision.md"
            decision_link = os_home / "memory/decisions/2026-05-10-0945-unsafe-decision.md"
            try:
                decision_link.symlink_to(outside_file)
            except (NotImplementedError, OSError) as error:
                self.skipTest(f"Symlink creation is unsupported: {error}")

            with self.assertRaises(ValueError):
                add_decision_memory(
                    os_home,
                    project_id="demo",
                    title="Unsafe Decision",
                    rationale="This should not write through the decision symlink.",
                    timestamp="2026-05-10 09:45",
                )

            self.assertFalse(outside_file.exists())

    def test_update_project_state_rejects_symlinked_project_state_directory_outside_os_home(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os_home = init_os(temp_dir)
            outside_dir = Path(temp_dir) / "outside-project-state"
            outside_dir.mkdir()
            shutil.rmtree(os_home / "memory/project-state")
            try:
                (os_home / "memory/project-state").symlink_to(outside_dir, target_is_directory=True)
            except (NotImplementedError, OSError) as error:
                self.skipTest(f"Symlink creation is unsupported: {error}")

            with self.assertRaises(ValueError):
                update_project_state(os_home, "demo", "Unsafe State", datetime(2026, 5, 10, 9, 30))

            self.assertFalse((outside_dir / "demo.md").exists())

    def test_update_project_state_rejects_hardlinked_project_state_file_without_writing_outside(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os_home = init_os(temp_dir)
            outside_file = Path(temp_dir) / "outside-project-state.md"
            project_state = os_home / "memory/project-state/demo.md"
            outside_file.write_text("outside state\n", encoding="utf-8")
            try:
                os.link(outside_file, project_state)
            except (NotImplementedError, OSError) as error:
                self.skipTest(f"Hardlink creation is unsupported: {error}")

            with self.assertRaises(ValueError):
                update_project_state(os_home, "demo", "Unsafe State", datetime(2026, 5, 10, 9, 30))

            self.assertEqual("outside state\n", outside_file.read_text(encoding="utf-8"))

    def test_memory_add_session_command_reports_invalid_project_id(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            init_os(temp_dir)
            stderr = io.StringIO()

            exit_code = main(
                [
                    "--os-home",
                    temp_dir,
                    "memory",
                    "add",
                    "session",
                    "--project-id",
                    "../../../escaped",
                    "--title",
                    "Unsafe Project",
                    "--summary",
                    "This should not write outside project state.",
                    "--timestamp",
                    "2026-05-10 09:30",
                ],
                stderr=stderr,
            )

            self.assertEqual(1, exit_code)
            self.assertIn("Error:", stderr.getvalue())

    def test_add_session_memory_creates_unique_session_files_for_duplicate_times(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os_home = init_os(temp_dir)

            first_path = add_session_memory(
                os_home,
                project_id="demo",
                title="Plan Agentic OS",
                summary="First session summary.",
                timestamp="2026-05-10 09:30",
            )
            second_path = add_session_memory(
                os_home,
                project_id="demo",
                title="Plan Agentic OS",
                summary="Second session summary.",
                timestamp="2026-05-10 09:30",
            )

            self.assertNotEqual(first_path, second_path)
            self.assertTrue(first_path.is_file())
            self.assertTrue(second_path.is_file())
            self.assertEqual("2026-05-10-0930-plan-agentic-os-2.md", second_path.name)
            self.assertIn("First session summary.", first_path.read_text(encoding="utf-8"))
            self.assertIn("Second session summary.", second_path.read_text(encoding="utf-8"))

    def test_memory_add_session_command_writes_session_and_project_state(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os_home = init_os(temp_dir)
            stdout = io.StringIO()

            exit_code = main(
                [
                    "--os-home",
                    temp_dir,
                    "memory",
                    "add",
                    "session",
                    "--project-id",
                    "demo",
                    "--title",
                    "Plan Agentic OS",
                    "--summary",
                    "Created the core MVP implementation plan.",
                    "--next-action",
                    "Review plan",
                    "--timestamp",
                    "2026-05-10 09:30",
                ],
                stdout=stdout,
            )

            self.assertEqual(0, exit_code)
            self.assertIn("Recorded session memory", stdout.getvalue())
            session_path = os_home / "memory/sessions/2026-05-10-0930-plan-agentic-os.md"
            self.assertTrue(session_path.is_file())
            self.assertIn("- Review plan", session_path.read_text(encoding="utf-8"))
            project_state = os_home / "memory/project-state/demo.md"
            self.assertTrue(project_state.is_file())
            self.assertIn("Plan Agentic OS", project_state.read_text(encoding="utf-8"))
