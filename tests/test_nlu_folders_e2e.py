"""Spoken folder reaches the real files: sentence -> NLU -> Actions -> throw-away HOME."""
import os

import pytest

if os.name == "nt":
    pytest.skip("file actions target Linux; runs on Ubuntu and in CI", allow_module_level=True)

pytest.importorskip("rapidfuzz")

import actions
from apps_files_support import BaseCase
from nlu import understand


def say(text, confirmed=False):
    intent = understand(text)
    if confirmed:
        intent["params"]["confirmed"] = True
    return actions.run(intent)


class FolderEndToEndTests(BaseCase):
    def test_file_goes_to_the_spoken_folder(self):
        self.assertOk(say("create file notes.txt in downloads"))
        self.assertTrue((self.downloads / "notes.txt").exists())
        self.assertFalse((self.docs / "notes.txt").exists())

    def test_no_folder_means_documents(self):
        self.assertOk(say("create file notes.txt"))
        self.assertTrue((self.docs / "notes.txt").exists())

    def test_folder_is_created_in_the_spoken_folder(self):
        self.assertOk(say("create folder projects in downloads"))
        self.assertTrue((self.downloads / "projects").is_dir())
        self.assertFalse((self.docs / "projects").exists())

    def test_new_file_types_work(self):
        for name in ("notes.md", "config.json", "run.sh"):
            self.assertOk(say(f"create file {name}"))
            self.assertTrue((self.docs / name).exists())

    def test_the_folder_resolves_the_same_name_in_two_places(self):
        (self.docs / "report.pdf").write_text("docs")
        (self.downloads / "report.pdf").write_text("downloads")

        # without a folder the name is ambiguous: nothing is asked or deleted
        result = say("delete report.pdf")
        self.assertEqual(result["status"], "error")

        # with a folder only that file is asked about, then deleted on yes
        self.assertEqual(say("delete report.pdf from downloads")["status"], "needs_confirmation")
        self.assertOk(say("delete report.pdf from downloads", confirmed=True))
        self.assertFalse((self.downloads / "report.pdf").exists())
        self.assertTrue((self.docs / "report.pdf").exists())

    def test_rename_in_the_spoken_folder(self):
        (self.docs / "old.txt").write_text("a")
        (self.downloads / "old.txt").write_text("b")
        self.assertOk(say("rename old.txt to new.txt in downloads"))
        self.assertTrue((self.downloads / "new.txt").exists())
        self.assertTrue((self.docs / "old.txt").exists())

    def test_read_only_folder_is_refused_not_silently_replaced_by_documents(self):
        result = say("create file notes.docx on the desktop")
        self.assertEqual(result["status"], "error")
        self.assertFalse((self.docs / "notes.docx").exists())
        self.assertFalse((self.desktop / "notes.docx").exists())
