import os
import shutil
import tempfile
import unittest
from pathlib import Path

from agentic_os.bootstrap import init_os
from agentic_os.memory import add_decision_memory, add_session_memory
from agentic_os.memory_index import list_memory, parse_front_matter, search_memory


class MemoryIndexTests(unittest.TestCase):
    def test_list_returns_latest_entries_first_across_session_and_decision(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os_home = init_os(temp_dir)
            add_session_memory(
                os_home,
                project_id="demo",
                title="Older Session",
                summary="Captured earlier session.",
                timestamp="2026-05-10 09:30",
            )
            add_decision_memory(
                os_home,
                project_id="demo",
                title="Newer Decision",
                rationale="Captured later decision.",
                timestamp="2026-05-10 09:45",
            )

            entries = list_memory(os_home)

            self.assertGreaterEqual(len(entries), 2)
            self.assertEqual("Newer Decision", entries[0].title)
            self.assertEqual("decision", entries[0].memory_type)
            self.assertEqual("2026-05-10 09:45", entries[0].timestamp)
            self.assertEqual("Older Session", entries[1].title)
            self.assertEqual("session", entries[1].memory_type)

    def test_list_filters_by_type(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os_home = init_os(temp_dir)
            add_session_memory(
                os_home,
                project_id="demo",
                title="Planning Session",
                summary="Captured a session.",
                timestamp="2026-05-10 09:30",
            )
            add_decision_memory(
                os_home,
                project_id="demo",
                title="Architecture Decision",
                rationale="Captured a decision.",
                timestamp="2026-05-10 09:45",
            )

            entries = list_memory(os_home, memory_type="session")

            self.assertEqual(["session"], [entry.memory_type for entry in entries])
            self.assertEqual(["Planning Session"], [entry.title for entry in entries])

    def test_search_returns_matching_snippet(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os_home = init_os(temp_dir)
            add_session_memory(
                os_home,
                project_id="demo",
                title="Searchable Session",
                summary="Needle appears in this summary line.",
                timestamp="2026-05-10 09:30",
            )

            results = search_memory(os_home, "needle")

            self.assertEqual(1, len(results))
            self.assertEqual("Searchable Session", results[0].title)
            self.assertEqual("Needle appears in this summary line.", results[0].snippet)

    def test_list_and_search_ignore_non_markdown_memory_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os_home = init_os(temp_dir)
            session_text = os_home / "memory/sessions/session.txt"
            session_backup = os_home / "memory/sessions/session.md.bak"
            hidden_text = os_home / "memory/sessions/.hidden.txt"
            project_state_text = os_home / "memory/project-state/demo.txt"
            for path in [session_text, session_backup, hidden_text]:
                path.write_text(
                    "\n".join(
                        [
                            "---",
                            'type: "session"',
                            'project_id: "demo"',
                            f'title: "Ignored {path.name}"',
                            'timestamp: "2026-05-10 09:30"',
                            "---",
                            "",
                            "Needle should not be searchable.",
                        ]
                    ),
                    encoding="utf-8",
                )
            project_state_text.write_text("Needle project state should not be searchable.", encoding="utf-8")

            entries = list_memory(os_home)
            results = search_memory(os_home, "needle")

            self.assertEqual([], entries)
            self.assertEqual([], results)

    def test_list_rejects_negative_limit(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os_home = init_os(temp_dir)

            with self.assertRaises(ValueError):
                list_memory(os_home, limit=-1)

    def test_parse_front_matter_handles_empty_tags_list_block(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "session.md"
            path.write_text(
                "\n".join(
                    [
                        "---",
                        'type: "session"',
                        'project_id: "demo"',
                        'title: "No Tags"',
                        'timestamp: "2026-05-10 09:30"',
                        "tags:",
                        "---",
                        "",
                        "# No Tags",
                    ]
                ),
                encoding="utf-8",
            )

            metadata = parse_front_matter(path)

            self.assertEqual("session", metadata["type"])
            self.assertEqual("demo", metadata["project_id"])
            self.assertEqual("No Tags", metadata["title"])
            self.assertEqual([], metadata["tags"])

    def test_symlinked_memory_file_and_directory_are_skipped(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os_home = init_os(temp_dir)
            outside_dir = Path(temp_dir) / "outside"
            outside_dir.mkdir()
            outside_file = outside_dir / "outside.md"
            outside_file.write_text(
                "\n".join(
                    [
                        "---",
                        'type: "session"',
                        'project_id: "demo"',
                        'title: "Outside Memory"',
                        'timestamp: "2026-05-10 09:30"',
                        "---",
                        "",
                        "Outside content",
                    ]
                ),
                encoding="utf-8",
            )

            file_link = os_home / "memory/sessions/linked.md"
            try:
                file_link.symlink_to(outside_file)
            except (NotImplementedError, OSError) as error:
                self.skipTest(f"Symlink creation is unsupported: {error}")

            shutil.rmtree(os_home / "memory/decisions")
            (os_home / "memory/decisions").symlink_to(outside_dir, target_is_directory=True)

            entries = list_memory(os_home)
            results = search_memory(os_home, "Outside")

            self.assertEqual([], [entry for entry in entries if entry.title == "Outside Memory"])
            self.assertEqual([], results)

    def test_hardlinked_memory_file_is_skipped(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os_home = init_os(temp_dir)
            outside_file = Path(temp_dir) / "outside.md"
            outside_file.write_text(
                "\n".join(
                    [
                        "---",
                        'type: "session"',
                        'project_id: "demo"',
                        'title: "Outside Memory"',
                        'timestamp: "2026-05-10 09:30"',
                        "---",
                        "",
                        "Outside content",
                    ]
                ),
                encoding="utf-8",
            )
            hardlink_path = os_home / "memory/sessions/hardlinked.md"
            try:
                os.link(outside_file, hardlink_path)
            except (NotImplementedError, OSError) as error:
                self.skipTest(f"Hardlink creation is unsupported: {error}")

            entries = list_memory(os_home)
            results = search_memory(os_home, "Outside")

            self.assertEqual([], [entry for entry in entries if entry.title == "Outside Memory"])
            self.assertEqual([], results)
