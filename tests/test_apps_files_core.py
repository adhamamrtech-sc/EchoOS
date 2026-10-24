"""Unit tests for actions/file_app_core (files, safety, confirmation, apps)."""
import os

import pytest

if os.name == "nt":
    pytest.skip("apps_files targets Linux (dir_fd, getuid); runs on Ubuntu and in CI", allow_module_level=True)

import errno
import os
import subprocess
from types import SimpleNamespace
from unittest import mock

from actions.file_app_core import apps, config, confirmation, files
from apps_files_support import BaseCase, FakePopen, FakeProc


class ListTests(BaseCase):
    def test_sorted_with_types_and_default_is_documents(self):
        (self.docs / "b.txt").touch()
        (self.docs / "A_folder").mkdir()
        r = files.list_files(None)
        self.assertOk(r)
        self.assertEqual([e["name"] for e in r["data"]["items"]], ["A_folder", "b.txt"])
        self.assertEqual(r["data"]["items"][0]["type"], "folder")
        self.assertIn("2 items", r["message"])

    def test_empty_hidden_and_truncated(self):
        self.assertIn("empty", files.list_files("documents")["message"])
        (self.docs / ".hidden").touch()
        self.assertEqual(files.list_files("documents")["data"]["items"], [])
        for i in range(9):
            (self.docs / f"f{i}").touch()
        r = files.list_files("documents")
        self.assertIn("and 4 more", r["message"])
        self.assertEqual(len(r["data"]["items"]), 9)

    def test_nlu_folder_names_english_and_arabic(self):
        (self.downloads / "d.txt").touch()
        (self.desktop / "e.txt").touch()
        for spoken in ("downloads", "التنزيلات", "التحميلات"):
            self.assertEqual(files.list_files(spoken)["data"]["items"][0]["name"], "d.txt", spoken)
        self.assertEqual(files.list_files("desktop")["data"]["items"][0]["name"], "e.txt")
        self.assertOk(files.list_files("pictures"))

    def test_subfolder_of_alias(self):
        (self.docs / "os").mkdir()
        (self.docs / "os" / "x").touch()
        self.assertEqual(files.list_files("documents/os")["data"]["items"][0]["name"], "x")

    def test_xdg_user_dirs_honoured(self):
        (self.home / ".config").mkdir()
        (self.home / ".config" / "user-dirs.dirs").write_text('XDG_DOCUMENTS_DIR="$HOME/Docs2"\n')
        (self.home / "Docs2").mkdir()
        (self.home / "Docs2" / "z").touch()
        self.assertEqual(files.list_files("documents")["data"]["items"][0]["name"], "z")

    def test_outside_safe_folders_refused(self):
        (self.home / "private").mkdir()
        for bad in ("/etc", str(self.home), str(self.home / "private"), self.docs / ".." / "private"):
            self.assertError(files.list_files(bad), "outside_safe_folders")

    def test_symlink_escape_refused(self):
        outside = self.home / "private"
        outside.mkdir()
        (self.docs / "link").symlink_to(outside)
        self.assertError(files.list_files("documents/link"), "outside_safe_folders")

    def test_missing_and_not_a_directory(self):
        self.assertError(files.list_files("documents/nope"), "not_found")
        (self.docs / "f").touch()
        self.assertError(files.list_files("documents/f"), "not_a_directory")

    def test_permission_error(self):
        with mock.patch("os.scandir", side_effect=PermissionError):
            self.assertError(files.list_files("documents"), "permission_denied")


class CreateTests(BaseCase):
    def test_create_file_and_folder_default_documents(self):
        self.assertOk(files.create_file(None, "notes.txt"))
        self.assertOk(files.create_folder(None, "projects"))
        self.assertTrue((self.docs / "notes.txt").is_file())
        self.assertTrue((self.docs / "projects").is_dir())

    def test_create_in_downloads_and_unicode(self):
        self.assertOk(files.create_file("downloads", "ملاحظات مهمة.txt"))
        self.assertOk(files.create_folder("التنزيلات", "مجلد جديد"))
        self.assertTrue((self.downloads / "ملاحظات مهمة.txt").exists())
        self.assertTrue((self.downloads / "مجلد جديد").is_dir())

    def test_never_overwrites(self):
        (self.docs / "a.txt").write_text("precious")
        self.assertError(files.create_file(None, "a.txt"), "already_exists")
        self.assertEqual((self.docs / "a.txt").read_text(), "precious")
        (self.docs / "dangling").symlink_to(self.docs / "missing")
        self.assertError(files.create_file(None, "dangling"), "already_exists")
        self.assertFalse((self.docs / "missing").exists())

    def test_invalid_names(self):
        for bad in ("", "   ", None, ".", "..", "../x", "a/b", "/abs", "x\x00y", "x\ny", 5, "a" * 300):
            self.assertError(files.create_file(None, bad))
        self.assertEqual(list(self.docs.iterdir()), [])

    def test_writes_refused_in_read_only_folders(self):
        self.assertError(files.create_file("desktop", "x"), "outside_safe_folders")
        self.assertError(files.create_folder("pictures", "x"), "outside_safe_folders")
        self.assertEqual(list(self.desktop.iterdir()) + list(self.pictures.iterdir()), [])

    def test_shell_metacharacters_are_a_plain_name(self):
        name = "$(touch pwned); rm -rf ~ `x`.txt"
        self.assertOk(files.create_file(None, name))
        self.assertEqual([p.name for p in self.docs.iterdir()], [name])

    def test_oserror_hides_internal_details(self):
        err = OSError(errno.ENOSPC, "No space left on device", "/secret/path")
        with mock.patch("os.mkdir", side_effect=err):
            r = files.create_folder(None, "x")
        self.assertError(r, "os_error")
        self.assertNotIn("/secret/path", r["message"])


class RenameTests(BaseCase):
    def test_rename_searches_documents_and_downloads(self):
        (self.docs / "a.txt").write_text("hi")
        (self.downloads / "dir").mkdir()
        self.assertOk(files.rename_item(None, "a.txt", "b.txt"))
        self.assertOk(files.rename_item(None, "dir", "dir2"))
        self.assertEqual((self.docs / "b.txt").read_text(), "hi")
        self.assertTrue((self.downloads / "dir2").is_dir())

    def test_explicit_folder_and_unicode(self):
        (self.downloads / "قديم.txt").touch()
        self.assertOk(files.rename_item("downloads", "قديم.txt", "جديد file.txt"))
        self.assertTrue((self.downloads / "جديد file.txt").exists())

    def test_missing_ambiguous_and_same_name(self):
        self.assertError(files.rename_item(None, "ghost", "x"), "not_found")
        (self.docs / "r.txt").touch()
        (self.downloads / "r.txt").touch()
        self.assertError(files.rename_item(None, "r.txt", "s.txt"), "ambiguous")
        self.assertTrue((self.docs / "r.txt").exists() and (self.downloads / "r.txt").exists())
        self.assertError(files.rename_item("documents", "r.txt", "r.txt"), "invalid_name")

    def test_never_replaces_destination(self):
        (self.docs / "a").write_text("A")
        (self.docs / "b").write_text("B")
        self.assertError(files.rename_item(None, "a", "b"), "already_exists")
        (self.docs / "d1").mkdir()
        (self.docs / "d2").mkdir()
        self.assertError(files.rename_item(None, "d1", "d2"), "already_exists")
        self.assertEqual((self.docs / "b").read_text(), "B")

    def test_fallback_without_renameat2(self):
        (self.docs / "a").write_text("A")
        (self.docs / "b").write_text("B")
        with mock.patch.object(files, "_renameat2", return_value=None):
            self.assertError(files.rename_item(None, "a", "b"), "already_exists")
            self.assertOk(files.rename_item(None, "a", "c"))
        self.assertEqual((self.docs / "c").read_text(), "A")

    def test_invalid_names(self):
        (self.docs / "a").touch()
        for old, new in (("a", "../evil"), ("../a", "b"), ("a", "")):
            self.assertError(files.rename_item(None, old, new))
        self.assertTrue((self.docs / "a").exists())


class DeleteTests(BaseCase):
    def _ask(self, name="victim.txt", content="x", folder=None):
        (self.docs / name).write_text(content)
        r = files.delete_file(folder, name)
        self.assertEqual(r["status"], "needs_confirmation", r)
        self.assertTrue((self.docs / name).exists())
        return r

    def test_unconfirmed_never_deletes(self):
        self._ask()
        r = files.delete_file(None, "victim.txt", confirmed=False)
        self.assertEqual(r["status"], "needs_confirmation")
        self.assertTrue((self.docs / "victim.txt").exists())

    def test_confirmed_after_request_deletes(self):
        self._ask()
        self.assertOk(files.delete_file(None, "victim.txt", confirmed=True))
        self.assertFalse((self.docs / "victim.txt").exists())

    def test_confirmed_flag_alone_is_not_enough(self):
        (self.docs / "victim.txt").write_text("x")
        r = files.delete_file(None, "victim.txt", confirmed=True)
        self.assertEqual(r["status"], "needs_confirmation")
        self.assertTrue((self.docs / "victim.txt").exists())

    def test_confirmation_is_single_use(self):
        self._ask()
        self.assertOk(files.delete_file(None, "victim.txt", confirmed=True))
        (self.docs / "victim.txt").write_text("again")
        self.assertEqual(files.delete_file(None, "victim.txt", confirmed=True)["status"], "needs_confirmation")
        self.assertTrue((self.docs / "victim.txt").exists())

    def test_confirmation_for_another_file_does_not_apply(self):
        self._ask("one.txt")
        (self.docs / "two.txt").write_text("2")
        r = files.delete_file(None, "two.txt", confirmed=True)
        self.assertEqual(r["status"], "needs_confirmation")
        self.assertTrue((self.docs / "two.txt").exists() and (self.docs / "one.txt").exists())

    def test_expired_confirmation(self):
        t = [100.0]
        with mock.patch.object(confirmation, "_now", lambda: t[0]):
            self._ask()
            t[0] += config.CONFIRMATION_TTL_SECONDS + 1
            self.assertEqual(files.delete_file(None, "victim.txt", confirmed=True)["status"], "needs_confirmation")
        self.assertTrue((self.docs / "victim.txt").exists())

    def test_changed_between_ask_and_confirm(self):
        self._ask(content="short")
        (self.docs / "victim.txt").write_text("a much longer replacement")
        self.assertError(files.delete_file(None, "victim.txt", confirmed=True), "changed")
        self.assertTrue((self.docs / "victim.txt").exists())

    def test_replaced_by_other_file_same_size(self):
        self._ask(content="same-size")
        (self.docs / "victim.txt").unlink()
        (self.docs / "victim.txt").write_text("same-size")
        self.assertError(files.delete_file(None, "victim.txt", confirmed=True), "changed")

    def test_removed_before_confirm(self):
        self._ask()
        (self.docs / "victim.txt").unlink()
        self.assertError(files.delete_file(None, "victim.txt", confirmed=True), "not_found")

    def test_folder_that_swapped_for_symlink_is_refused(self):
        (self.docs / "d").mkdir()
        (self.docs / "d" / "f").write_text("keep")
        files.delete_file("documents/d", "f")
        other = self.docs / "other"
        other.mkdir()
        (other / "f").write_text("keep too")
        (self.docs / "d" / "f").rename(self.docs / "moved")
        (self.docs / "d").rmdir()
        (self.docs / "d").symlink_to(other)
        self.assertEqual(files.delete_file("documents/d", "f", confirmed=True)["status"], "needs_confirmation")
        self.assertTrue((other / "f").exists())

    def test_finds_file_in_downloads_and_reports_ambiguity(self):
        (self.downloads / "report.pdf").write_text("p")
        r = files.delete_file(None, "report.pdf")
        self.assertIn("Downloads", r["message"])
        self.assertOk(files.delete_file(None, "report.pdf", confirmed=True))
        (self.docs / "dup.txt").touch()
        (self.downloads / "dup.txt").touch()
        self.assertError(files.delete_file(None, "dup.txt"), "ambiguous")

    def test_refuses_folders_special_files_missing_and_outside(self):
        (self.docs / "dir").mkdir()
        self.assertError(files.delete_file(None, "dir"), "is_directory")
        os.mkfifo(self.docs / "pipe")
        self.assertError(files.delete_file(None, "pipe"), "unsupported_type")
        self.assertError(files.delete_file(None, "ghost"), "not_found")
        self.assertError(files.delete_file("desktop", "x"), "outside_safe_folders")
        self.assertFalse(confirmation.has_pending())

    def test_symlink_removes_link_not_target(self):
        target = self.docs / "target.txt"
        target.write_text("keep")
        (self.docs / "lnk").symlink_to(target)
        files.delete_file(None, "lnk")
        self.assertOk(files.delete_file(None, "lnk", confirmed=True))
        self.assertFalse((self.docs / "lnk").is_symlink())
        self.assertEqual(target.read_text(), "keep")

    def test_unicode_and_unlink_failure(self):
        self._ask("تقرير نهائي.txt")
        with mock.patch("os.unlink", side_effect=PermissionError):
            self.assertError(files.delete_file(None, "تقرير نهائي.txt", confirmed=True), "permission_denied")
        self.assertTrue((self.docs / "تقرير نهائي.txt").exists())


class NluNormalisedNameTests(BaseCase):
    """nlu/normalize.py lower-cases and folds Arabic letters before names reach us."""

    def test_delete_and_rename_match_mixed_case_names(self):
        (self.docs / "Report.PDF").write_text("p")
        r = files.delete_file(None, "report.pdf")
        self.assertEqual(r["status"], "needs_confirmation")
        self.assertEqual(r["target"] if "target" in r else r["data"]["target"], "Report.PDF")
        self.assertOk(files.delete_file(None, "report.pdf", confirmed=True))
        self.assertFalse((self.docs / "Report.PDF").exists())
        (self.docs / "Old.TXT").write_text("x")
        self.assertOk(files.rename_item(None, "old.txt", "new.txt"))
        self.assertTrue((self.docs / "new.txt").exists())

    def test_arabic_letter_folding(self):
        (self.docs / "مقالة أحمد.txt").write_text("x")      # spoken form arrives as ه / ا
        r = files.delete_file(None, "مقاله احمد.txt")
        self.assertEqual(r["status"], "needs_confirmation")
        self.assertOk(files.delete_file(None, "مقاله احمد.txt", confirmed=True))
        self.assertFalse((self.docs / "مقالة أحمد.txt").exists())

    def test_exact_name_wins_and_ambiguity_is_refused(self):
        (self.docs / "a.txt").touch()
        (self.docs / "A.txt").touch()
        self.assertEqual(files.delete_file("documents", "a.txt")["status"], "needs_confirmation")
        confirmation.clear()
        self.assertError(files.delete_file("documents", "a.TXT"), "ambiguous")
        self.assertTrue((self.docs / "a.txt").exists() and (self.docs / "A.txt").exists())


class AppAliasTests(BaseCase):
    def test_nlu_keys_and_aliases_resolve(self):
        for spoken, key in {
            "firefox": "firefox", "Firefox": "firefox", "chrome": "chrome", "كروم": "chrome",
            "vscode": "vscode", "terminal": "terminal", "الطرفية": "terminal", "spotify": "spotify",
            "vlc": "vlc", "calculator": "calculator", "files": "files", "مدير الملفات": "files",
            "settings": "settings", "الاعدادات": "settings", "the firefox": "firefox",
        }.items():
            self.assertEqual(apps.find_app(spoken).key, key, spoken)

    def test_no_partial_or_unknown_matches(self):
        for bad in ("fire", "chorme", "rm -rf", "firefox; rm -rf /", "../../bin/sh", "", None, 5):
            self.assertIsNone(apps.find_app(bad), bad)


class OpenAppTests(BaseCase):
    def test_exact_argv_no_shell(self):
        self.use_fake_popen()
        self.installed("firefox")
        r = apps.open_app("firefox")
        self.assertOk(r)
        argv, kwargs = FakePopen.calls[0]
        self.assertEqual(argv, ["firefox"])
        self.assertNotIn("shell", kwargs)
        self.assertTrue(kwargs["start_new_session"])
        self.assertEqual(r["message"], "Opening Firefox.")

    def test_fallback_commands_in_dana_order(self):
        self.use_fake_popen()
        self.installed("chromium-browser")
        self.assertOk(apps.open_app("chrome"))
        self.assertEqual(FakePopen.calls[0][0], ["chromium-browser"])
        FakePopen.reset()
        self.installed("galculator")
        self.assertOk(apps.open_app("calculator"))
        self.assertEqual(FakePopen.calls[0][0], ["galculator"])

    def test_files_fallback_uses_home_not_cwd(self):
        self.use_fake_popen()
        self.installed("xdg-open")
        self.assertOk(apps.open_app("files"))
        self.assertEqual(FakePopen.calls[0][0], ["xdg-open", str(self.home)])

    def test_not_installed_and_launch_failed(self):
        self.use_fake_popen()
        self.installed()
        self.assertError(apps.open_app("firefox"), "not_installed")
        self.installed("firefox")
        FakePopen.returncode = 1
        self.assertError(apps.open_app("firefox"), "launch_failed")

    def test_no_display_is_reported_when_launch_fails(self):
        self.use_fake_popen()
        self.installed("firefox")
        FakePopen.returncode = 1
        os.environ.pop("DISPLAY", None)
        os.environ.pop("WAYLAND_DISPLAY", None)
        self.assertError(apps.open_app("firefox"), "no_display")

    def test_exit_zero_and_mock_returncode_count_as_launched(self):
        self.use_fake_popen()
        self.installed("firefox")
        FakePopen.returncode = 0
        self.assertOk(apps.open_app("firefox"))
        FakePopen.returncode = mock.MagicMock()  # what a bare Mock Popen returns
        self.assertOk(apps.open_app("firefox"))

    def test_gtk_launch_fallback(self):
        self.installed("gtk-launch")
        calls = []
        with mock.patch.object(subprocess, "run", lambda a, **k: calls.append(a) or SimpleNamespace(returncode=0)):
            self.assertOk(apps.open_app("calculator"))
        self.assertEqual(calls, [["/usr/bin/gtk-launch", "org.gnome.Calculator.desktop"]])

    def test_unsupported_and_injection_never_spawn(self):
        self.use_fake_popen()
        self.installed("firefox")
        for bad in ("banana", "firefox; rm -rf ~", "$(reboot)", "/bin/sh", "rm -rf"):
            self.assertError(apps.open_app(bad), "unsupported_app")
        for bad in (None, "", " ", 3):
            self.assertError(apps.open_app(bad), "missing_parameter")
        self.assertEqual(FakePopen.calls, [])

    def test_open_folder_safe_and_unsafe(self):
        self.use_fake_popen()
        self.installed("xdg-open")
        self.assertOk(apps.open_folder("downloads"))
        self.assertEqual(FakePopen.calls[0][0], ["xdg-open", str(self.downloads)])
        FakePopen.reset()
        self.assertError(apps.open_folder("/etc"), "outside_safe_folders")
        self.assertError(apps.open_folder(str(self.home)), "outside_safe_folders")
        self.assertEqual(FakePopen.calls, [])


class CloseAppTests(BaseCase):
    def test_not_running(self):
        r = apps.close_app("firefox")
        self.assertOk(r)
        self.assertEqual(r["data"]["closed"], 0)
        self.assertIn("not running", r["message"])

    def test_closes_parent_only_with_sigterm(self):
        parent, child = FakeProc(10, "chrome"), FakeProc(11, "chrome", ppid=10)
        self.psutil.procs = [parent, child]
        r = apps.close_app("chrome")
        self.assertOk(r)
        self.assertTrue(parent.terminated)
        self.assertFalse(child.terminated)
        self.assertEqual(r["message"], "Closed Chrome.")

    def test_exact_names_only(self):
        procs = [FakeProc(10, "firefox-esr-helper"), FakeProc(11, "notfirefox"),
                 FakeProc(12, "python3", cmdline=["python3", "firefox"]), FakeProc(13, "systemd")]
        self.psutil.procs = procs
        self.assertEqual(apps.close_app("firefox")["data"]["closed"], 0)
        self.assertFalse(any(p.terminated for p in procs))

    def test_truncated_process_name_matches_by_cmdline(self):
        proc = FakeProc(10, "gnome-calculato", cmdline=["/usr/bin/gnome-calculator"])
        self.psutil.procs = [proc]
        self.assertOk(apps.close_app("calculator"))
        self.assertTrue(proc.terminated)

    def test_other_users_untouched(self):
        other = FakeProc(10, "firefox", uid=os.getuid() + 1)
        self.psutil.procs = [other]
        self.assertEqual(apps.close_app("firefox")["data"]["closed"], 0)
        self.assertFalse(other.terminated)

    def test_never_closes_own_terminal(self):
        term = FakeProc(77, "gnome-terminal-server")
        self.psutil.procs, self.psutil.ancestors = [term], [SimpleNamespace(pid=77)]
        self.assertError(apps.close_app("terminal"), "self_protected")
        self.assertFalse(term.terminated)

    def test_stubborn_app_reported_not_killed(self):
        proc = FakeProc(10, "vlc", closes=False)
        self.psutil.procs = [proc]
        self.assertError(apps.close_app("vlc"), "close_timeout")

    def test_denied_unsupported_and_missing_psutil(self):
        self.psutil.procs = [FakeProc(10, "firefox", deny=True), FakeProc(1, "sshd")]
        self.assertError(apps.close_app("firefox"), "permission_denied")
        for bad in ("sshd", "systemd", "*", "firefox; killall -9 python"):
            self.assertError(apps.close_app(bad), "unsupported_app")
        self.assertError(apps.close_app(None), "missing_parameter")
        with mock.patch.object(apps, "_get_psutil", lambda: None):
            self.assertError(apps.close_app("firefox"), "missing_dependency")
