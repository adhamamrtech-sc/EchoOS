"""Shared fixtures for the apps_files tests (plain unittest, runs under pytest too).

Each test gets a throw-away HOME (with Documents/Downloads/Desktop/Pictures), blocked
real subprocesses, a fake psutil (no real process is inspected or killed) and no delays.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from actions.file_app_core import apps, config, confirmation


class FakeProc:
    def __init__(self, pid, name, cmdline=None, ppid=1, uid=None, closes=True, deny=False):
        self.pid = pid
        self.info = {
            "pid": pid, "ppid": ppid, "name": name,
            "cmdline": cmdline if cmdline is not None else [name],
            "uids": SimpleNamespace(real=os.getuid() if uid is None else uid),
        }
        self.closes, self.deny, self.terminated = closes, deny, False

    def terminate(self):
        if self.deny:
            raise FakePsutil.AccessDenied()
        self.terminated = True


class FakePsutil:
    class NoSuchProcess(Exception):
        pass

    class AccessDenied(Exception):
        pass

    def __init__(self, procs=None, ancestors=()):
        self.procs = list(procs or [])
        self.ancestors = [SimpleNamespace(pid=p) for p in ancestors]

    def process_iter(self, attrs=None):
        return list(self.procs)

    def Process(self):  # noqa: N802
        return SimpleNamespace(parents=lambda: self.ancestors)

    def wait_procs(self, procs, timeout=None):
        gone = [p for p in procs if p.terminated and p.closes]
        return gone, [p for p in procs if p not in gone]


class FakePopen:
    calls: list = []
    returncode = None

    def __init__(self, argv, **kwargs):
        FakePopen.calls.append((argv, kwargs))

    def poll(self):
        return FakePopen.returncode

    def wait(self):
        return FakePopen.returncode

    @classmethod
    def reset(cls):
        cls.calls, cls.returncode = [], None


def _blocked(*args, **kwargs):
    raise AssertionError("A real subprocess was attempted in a unit test")


class BaseCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.home = Path(tmp.name).resolve() / "home"
        self.docs, self.downloads = self.home / "Documents", self.home / "Downloads"
        self.desktop, self.pictures = self.home / "Desktop", self.home / "Pictures"
        for folder in (self.docs, self.downloads, self.desktop, self.pictures):
            folder.mkdir(parents=True)

        env = mock.patch.dict(os.environ, {
            "HOME": str(self.home), "XDG_CONFIG_HOME": str(self.home / ".config"), "DISPLAY": ":0",
        })
        env.start()
        self.addCleanup(env.stop)
        os.environ.pop(config.ENV_READ_ROOTS, None)
        os.environ.pop(config.ENV_WRITE_ROOTS, None)

        for target, attr, value in (
            (subprocess, "Popen", _blocked), (subprocess, "run", _blocked),
            (config, "LAUNCH_SETTLE_SECONDS", 0),
        ):
            patcher = mock.patch.object(target, attr, value)
            patcher.start()
            self.addCleanup(patcher.stop)

        self.psutil = FakePsutil()
        patcher = mock.patch.object(apps, "_get_psutil", lambda: self.psutil)
        patcher.start()
        self.addCleanup(patcher.stop)

        FakePopen.reset()
        confirmation.clear()
        self.addCleanup(confirmation.clear)

    def use_fake_popen(self):
        patcher = mock.patch.object(subprocess, "Popen", FakePopen)
        patcher.start()
        self.addCleanup(patcher.stop)

    def installed(self, *names):
        patcher = mock.patch.object(apps.shutil, "which", lambda n: f"/usr/bin/{n}" if n in names else None)
        patcher.start()
        self.addCleanup(patcher.stop)

    def assertOk(self, result, msg=None):
        self.assertEqual(result["status"], "ok", msg or result)

    def assertError(self, result, code=None):
        self.assertEqual(result["status"], "error", result)
        if code:
            self.assertEqual(result["error_code"], code, result)
