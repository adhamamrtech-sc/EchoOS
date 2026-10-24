"""Integration with the team's code: intents shaped exactly like nlu/entities.py output,
sent through the Team Leader's actions.run() allowlist, with main.py's confirmation flow."""
import os

import pytest

if os.name == "nt":
    pytest.skip("apps_files targets Linux (dir_fd, getuid); runs on Ubuntu and in CI", allow_module_level=True)

import importlib.util
import unittest
from unittest import mock

import actions
from actions import apps_files
from apps_files_support import BaseCase, FakePopen, FakeProc


def intent(action, target=None, **params):
    """Same keys as nlu.understand() returns."""
    return {"action": action, "target": target, "params": params, "score": 1.0,
            "confidence": 1.0, "confidence_label": "high", "status": "ok"}


# What NLU emits (nlu/catalog.py + nlu/entities.py): note the literal targets
# "file", "files", "folder" that must NOT be mistaken for names.
NLU_SHAPES = {
    "open_app": intent("open_app", "firefox"),
    "close_app": intent("close_app", "firefox"),
    "open_folder": intent("open_folder", "downloads"),
    "list_files": intent("list_files", "files", folder="documents"),
    "create_file": intent("create_file", "file", filename="notes.txt"),
    "create_folder": intent("create_folder", "folder", name="projects"),
    "rename_file": intent("rename_file", "file", old="a.txt", new="b.txt"),
    "delete_file": intent("delete_file", "file", filename="report.pdf"),
}


def main_like(run, original, says_yes):
    """The confirmation logic of main.py: ask, then re-run the SAME intent with confirmed=True."""
    result = run(original)
    if result["status"] == "needs_confirmation":
        if says_yes:
            original["params"]["confirmed"] = True
            result = run(original)
        else:
            result = {"status": "ok", "message": "Cancelled."}
    return result


class AllowlistedCase(BaseCase):
    def setUp(self):
        super().setUp()
        patcher = mock.patch.dict(actions.ALLOWED_ACTIONS, apps_files.ACTIONS)
        patcher.start()
        self.addCleanup(patcher.stop)


class ContractTests(AllowlistedCase):
    def test_every_handler_returns_status_and_message(self):
        self.use_fake_popen()
        self.installed("firefox", "xdg-open")
        for name, original in NLU_SHAPES.items():
            r = actions.run(dict(original, params=dict(original["params"])))
            self.assertIn(r["status"], {"ok", "error", "needs_confirmation"}, name)
            self.assertTrue(isinstance(r["message"], str) and r["message"], name)

    def test_handlers_survive_bad_intents(self):
        self.use_fake_popen()
        self.installed()  # nothing installed: no program can be started by accident
        for name, handler in apps_files.ACTIONS.items():
            for bad in (None, "x", [], {}, {"params": None}, {"params": "oops"}, {"target": 5, "params": {"filename": 7}}):
                r = handler(bad)
                self.assertIn(r["status"], {"ok", "error", "needs_confirmation"}, (name, bad))
                self.assertIn("message", r)

    def test_no_new_handler_leaks_exceptions_through_run(self):
        r = actions.run({"action": "create_file", "target": "file", "params": {"filename": "../../etc/passwd"}})
        self.assertEqual(r["status"], "error")


class NluShapedIntentTests(AllowlistedCase):
    def test_create_list_rename_via_nlu_shapes(self):
        self.assertOk(actions.run(NLU_SHAPES["create_folder"]))
        self.assertTrue((self.docs / "projects").is_dir())      # target "folder" was not used as a name
        self.assertOk(actions.run(NLU_SHAPES["create_file"]))
        self.assertTrue((self.docs / "notes.txt").exists())     # target "file" was not used as a name
        r = actions.run(NLU_SHAPES["list_files"])
        self.assertEqual([e["name"] for e in r["data"]["items"]], ["notes.txt", "projects"])
        self.assertEqual(sorted(p.name for p in self.docs.iterdir()), ["notes.txt", "projects"])
        (self.docs / "a.txt").write_text("hi")
        self.assertOk(actions.run(NLU_SHAPES["rename_file"]))
        self.assertTrue((self.docs / "b.txt").exists())

    def test_list_files_target_files_is_not_a_folder(self):
        r = actions.run(intent("list_files", "files"))       # no folder given -> Documents
        self.assertOk(r)
        self.assertEqual(r["data"]["path"], str(self.docs))

    def test_open_close_app(self):
        self.use_fake_popen()
        self.installed("firefox")
        self.assertOk(actions.run(NLU_SHAPES["open_app"]))
        self.assertEqual(FakePopen.calls[0][0], ["firefox"])
        proc = FakeProc(600, "firefox")
        self.psutil.procs = [proc]
        self.assertOk(actions.run(NLU_SHAPES["close_app"]))
        self.assertTrue(proc.terminated)

    def test_open_folder_target_alias(self):
        self.use_fake_popen()
        self.installed("xdg-open")
        self.assertOk(actions.run(NLU_SHAPES["open_folder"]))
        self.assertEqual(FakePopen.calls[0][0], ["xdg-open", str(self.downloads)])

    def test_same_checks_as_team_test_for_open_app(self):
        # mirrors tests/test_nlu_actions.py::test_open_app_works_end_to_end and ::rejects_unknown
        with mock.patch("shutil.which", return_value="/usr/bin/firefox"), \
             mock.patch("subprocess.Popen") as popen:
            result = actions.run(intent("open_app", "firefox"))
        self.assertEqual(result["status"], "ok")
        self.assertEqual(popen.call_args[0][0], ["firefox"])
        self.assertNotIn("shell", popen.call_args[1])
        self.assertEqual(actions.run({"action": "open_app", "target": "rm -rf", "params": {}})["status"], "error")


class MainConfirmationFlowTests(AllowlistedCase):
    def test_delete_after_yes(self):
        (self.downloads / "report.pdf").write_text("p")
        r = main_like(actions.run, intent("delete_file", "file", filename="report.pdf"), says_yes=True)
        self.assertOk(r)
        self.assertFalse((self.downloads / "report.pdf").exists())

    def test_cancel_keeps_file(self):
        (self.docs / "report.pdf").write_text("p")
        r = main_like(actions.run, intent("delete_file", "file", filename="report.pdf"), says_yes=False)
        self.assertEqual(r["message"], "Cancelled.")
        self.assertTrue((self.docs / "report.pdf").exists())

    def test_prompt_is_speakable(self):
        (self.docs / "report.pdf").write_text("p")
        r = actions.run(intent("delete_file", "file", filename="report.pdf"))
        self.assertEqual(r["status"], "needs_confirmation")
        self.assertEqual(r["message"], "Delete report.pdf from Documents? Say yes to confirm.")

    def test_forged_confirmed_flag_deletes_nothing(self):
        (self.docs / "report.pdf").write_text("p")
        r = actions.run(intent("delete_file", "file", filename="report.pdf", confirmed=True))
        self.assertEqual(r["status"], "needs_confirmation")
        self.assertTrue((self.docs / "report.pdf").exists())

    def test_other_apps_files_command_drops_pending_delete(self):
        (self.docs / "report.pdf").write_text("p")
        actions.run(intent("delete_file", "file", filename="report.pdf"))
        actions.run(intent("list_files", "files"))
        r = actions.run(intent("delete_file", "file", filename="report.pdf", confirmed=True))
        self.assertEqual(r["status"], "needs_confirmation")
        self.assertTrue((self.docs / "report.pdf").exists())


@unittest.skipUnless(importlib.util.find_spec("rapidfuzz") and importlib.util.find_spec("nlu"),
                     "needs the team's nlu package and rapidfuzz (present in the real repo / CI)")
class RealNluTests(AllowlistedCase):
    def test_spoken_sentences_end_to_end(self):
        from nlu import understand
        self.assertOk(actions.run(understand("create folder projects")))
        self.assertOk(actions.run(understand("create file notes.txt")))
        self.assertTrue((self.docs / "projects").is_dir() and (self.docs / "notes.txt").exists())
        self.assertOk(actions.run(understand("list files in documents")))
        (self.docs / "old.txt").touch()
        self.assertOk(actions.run(understand("rename old.txt to new.txt")))
        self.assertTrue((self.docs / "new.txt").exists())
        self.assertOk(actions.run(understand("اعرض الملفات في المستندات")))

    def test_every_nlu_action_we_own_is_registered(self):
        from nlu.catalog import COMMANDS
        nlu_actions = {c.action for c in COMMANDS}
        self.assertLessEqual(set(apps_files.ACTIONS), nlu_actions)
