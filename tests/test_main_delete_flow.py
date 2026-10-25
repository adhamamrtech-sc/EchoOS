"""Delete a file through the REAL main(): heard sentence -> NLU -> Actions -> spoken yes/no.

Only the microphone, the speech model and the speaker are fake. Everything else
(main.py, nlu/, actions/, file_app_core/) is the real code, working on a
throw-away HOME, never on real files.
"""
import os

import pytest

if os.name == "nt":
    pytest.skip("file actions target Linux; runs on Ubuntu and in CI", allow_module_level=True)

pytest.importorskip("rapidfuzz")

from apps_files_support import BaseCase
from test_main_flow import load_main

from actions.file_app_core import config, confirmation


def run_main(heard):
    """Run main() once. `heard` may be a list or a generator (to act between steps)."""
    loaded, said = load_main(heard)
    loaded.main()
    return said


class DeleteThroughMainTests(BaseCase):
    def make(self, folder, name="report.pdf", text="data"):
        path = folder / name
        path.write_text(text)
        return path

    def test_yes_deletes_only_the_asked_file(self):
        target = self.make(self.docs)
        other = self.make(self.docs, "notes.txt")
        said = run_main(["Delete report.pdf.", "Yes."])
        self.assertFalse(target.exists())
        self.assertTrue(other.exists())
        self.assertEqual(said[-1], "Deleted report.pdf.")

    def test_the_question_is_spoken_before_anything_is_deleted(self):
        target = self.make(self.docs)
        said = run_main(["delete report.pdf", "no"])
        self.assertEqual(said[0], "Delete report.pdf from Documents? Say yes to confirm.")
        self.assertTrue(target.exists())

    def test_no_keeps_the_file(self):
        target = self.make(self.docs)
        said = run_main(["delete report.pdf", "no"])
        self.assertTrue(target.exists())
        self.assertEqual(said[-1], "Cancelled.")

    def test_unclear_answers_keep_the_file(self):
        for answer in ("yesterday", "I didn't say yes", "maybe", "yes but wait", ""):
            target = self.make(self.docs)
            confirmation.clear()
            run_main(["delete report.pdf", answer])
            self.assertTrue(target.exists(), answer)

    def test_expired_confirmation_keeps_the_file(self):
        target = self.make(self.docs)
        with unittest_patch(config, "CONFIRMATION_TTL_SECONDS", -1.0):
            said = run_main(["delete report.pdf", "yes"])
        self.assertTrue(target.exists())
        self.assertNotIn("Deleted report.pdf.", said)

    def test_file_changed_between_question_and_yes_keeps_it(self):
        target = self.make(self.docs)

        def heard():
            yield "delete report.pdf"
            target.write_text("someone edited this file, so it is a different file now")
            yield "yes"

        said = run_main(heard())
        self.assertTrue(target.exists())
        self.assertIn("changed", said[-1])

    def test_file_replaced_between_question_and_yes_keeps_it(self):
        target = self.make(self.docs, text="aaaa")

        def heard():
            yield "delete report.pdf"
            target.unlink()
            target.write_text("bbbb")  # same name, same size, new file
            yield "yes"

        run_main(heard())
        self.assertTrue(target.exists())

    def test_same_name_in_two_folders_deletes_neither(self):
        a = self.make(self.docs)
        b = self.make(self.downloads)
        said = run_main(["delete report.pdf", "yes"])
        self.assertTrue(a.exists() and b.exists())
        self.assertIn("Documents and Downloads", said[-1])

    def test_a_folder_is_never_deleted(self):
        folder = self.docs / "report.pdf"
        folder.mkdir()
        run_main(["delete report.pdf", "yes"])
        self.assertTrue(folder.is_dir())

    def test_symlink_deletes_the_link_not_its_target(self):
        outside = self.home / "outside.txt"
        outside.write_text("keep me")
        link = self.docs / "report.pdf"
        link.symlink_to(outside)
        run_main(["delete report.pdf", "yes"])
        self.assertFalse(link.exists() and link.is_symlink())
        self.assertTrue(outside.exists())

    def test_nothing_is_deleted_when_the_file_does_not_exist(self):
        keep = self.make(self.docs, "notes.txt")
        said = run_main(["delete report.pdf"])
        self.assertTrue(keep.exists())
        self.assertIn("could not find", said[-1])


def unittest_patch(obj, name, value):
    from unittest import mock
    return mock.patch.object(obj, name, value)
