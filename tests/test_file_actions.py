import os

import pytest

from actions.file_app_core import confirmation, files


@pytest.fixture
def safe_folder(tmp_path, monkeypatch):
    monkeypatch.setenv("ECHOOS_WRITE_ROOTS", str(tmp_path))
    monkeypatch.setenv("ECHOOS_READ_ROOTS", str(tmp_path))
    confirmation.clear()
    yield tmp_path
    confirmation.clear()


def test_delete_first_call_only_requests_confirmation(safe_folder):
    target = safe_folder / "report.txt"
    target.write_text("important data")

    result = files.delete_file(safe_folder, "report.txt")

    assert result["status"] == "needs_confirmation"
    assert target.exists()


def test_delete_with_valid_confirmation(safe_folder):
    target = safe_folder / "report.txt"
    target.write_text("important data")

    first = files.delete_file(safe_folder, "report.txt")
    assert first["status"] == "needs_confirmation"

    second = files.delete_file(safe_folder, "report.txt", confirmed=True)

    assert second["status"] == "ok"
    assert not target.exists()


def test_confirmed_flag_without_pending_request_is_not_enough(safe_folder):
    target = safe_folder / "report.txt"
    target.write_text("important data")

    result = files.delete_file(
        safe_folder, "report.txt", confirmed=True
    )

    assert result["status"] == "needs_confirmation"
    assert target.exists()


def test_modified_file_cannot_be_deleted_after_confirmation_request(safe_folder):
    target = safe_folder / "report.txt"
    target.write_text("original data")

    first = files.delete_file(safe_folder, "report.txt")
    assert first["status"] == "needs_confirmation"

    target.write_text("changed data with a different length")

    result = files.delete_file(
        safe_folder, "report.txt", confirmed=True
    )

    assert result["status"] == "error"
    assert result["error_code"] == "changed"
    assert target.exists()


def test_expired_confirmation_cannot_delete_file(safe_folder, monkeypatch):
    target = safe_folder / "report.txt"
    target.write_text("important data")

    clock = [100.0]
    monkeypatch.setattr(confirmation, "_now", lambda: clock[0])

    first = files.delete_file(safe_folder, "report.txt")
    assert first["status"] == "needs_confirmation"

    clock[0] += files.config.CONFIRMATION_TTL_SECONDS + 1

    result = files.delete_file(
        safe_folder, "report.txt", confirmed=True
    )

    assert result["status"] == "needs_confirmation"
    assert target.exists()


def test_confirmation_is_single_use(safe_folder):
    target = safe_folder / "report.txt"
    target.write_text("important data")

    first = files.delete_file(safe_folder, "report.txt")
    assert first["status"] == "needs_confirmation"

    second = files.delete_file(
        safe_folder, "report.txt", confirmed=True
    )
    assert second["status"] == "ok"
    assert not target.exists()

    target.write_text("new important data")

    third = files.delete_file(
        safe_folder, "report.txt", confirmed=True
    )
    assert third["status"] == "needs_confirmation"
    assert target.exists()


def test_duplicate_filename_requires_folder_selection(safe_folder, monkeypatch):
    first_folder = safe_folder / "documents"
    second_folder = safe_folder / "downloads"

    first_folder.mkdir()
    second_folder.mkdir()

    monkeypatch.setenv(
        "ECHOOS_WRITE_ROOTS",
        os.pathsep.join((str(first_folder), str(second_folder))),
    )

    (first_folder / "report.txt").write_text("first")
    (second_folder / "report.txt").write_text("second")

    result = files.delete_file(None, "report.txt")

    assert result["status"] == "error"
    assert result["error_code"] == "ambiguous"
    assert (first_folder / "report.txt").exists()
    assert (second_folder / "report.txt").exists()


def test_directory_cannot_be_deleted(safe_folder):
    target = safe_folder / "important_folder"
    target.mkdir()

    result = files.delete_file(safe_folder, "important_folder")

    assert result["status"] == "error"
    assert result["error_code"] == "is_directory"
    assert target.is_dir()



