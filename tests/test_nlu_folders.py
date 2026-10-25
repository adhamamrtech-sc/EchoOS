"""The NLU passes "in <folder>" on to the file actions, and knows more file types."""
import pytest

pytest.importorskip("rapidfuzz")

from nlu import understand


@pytest.mark.parametrize("text, action, params", [
    # no folder said: no folder param (Dana's code then uses Documents)
    ("create file notes.txt", "create_file", {"filename": "notes.txt"}),
    ("create folder projects", "create_folder", {"name": "projects"}),
    ("delete report.pdf", "delete_file", {"filename": "report.pdf"}),
    ("rename old.txt to new.txt", "rename_file", {"old": "old.txt", "new": "new.txt"}),
    # folder said
    ("create file notes.txt in downloads", "create_file",
     {"filename": "notes.txt", "folder": "downloads"}),
    ("Create a file report.md in the downloads folder.", "create_file",
     {"filename": "report.md", "folder": "downloads"}),
    ("create folder projects in downloads", "create_folder",
     {"name": "projects", "folder": "downloads"}),
    ("delete report.pdf from downloads", "delete_file",
     {"filename": "report.pdf", "folder": "downloads"}),
    ("rename old.txt to new.txt in downloads", "rename_file",
     {"old": "old.txt", "new": "new.txt", "folder": "downloads"}),
    ("create file notes.docx on the desktop", "create_file",
     {"filename": "notes.docx", "folder": "desktop"}),
    # Arabic
    ("انشئ ملف notes.txt في التنزيلات", "create_file",
     {"filename": "notes.txt", "folder": "downloads"}),
    ("احذف الملف report.pdf من التحميلات", "delete_file",
     {"filename": "report.pdf", "folder": "downloads"}),
    ("اعمل فولدر مشاريع في المستندات", "create_folder",
     {"name": "مشاريع", "folder": "documents"}),
    ("اعمل فولدر مشاريع", "create_folder", {"name": "مشاريع"}),
    # a folder name used as the NAME of the new folder is not a location
    ("create folder documents", "create_folder", {"name": "documents"}),
    # unchanged behaviour
    ("list files in downloads", "list_files", {"folder": "downloads"}),
    ("list files", "list_files", {}),
])
def test_folder_param(text, action, params):
    intent = understand(text)
    assert intent["action"] == action, intent
    assert intent["params"] == params


@pytest.mark.parametrize("name", [
    "notes.md", "config.json", "run.sh", "index.html", "style.css", "app.js",
    "server.log", "data.xml", "settings.yml", "settings.yaml", "setup.ini",
    "report.pdf", "notes.txt", "photo.jpg", "main.py",
])
def test_more_file_types_are_understood(name):
    intent = understand(f"create file {name}")
    assert intent["action"] == "create_file", intent
    assert intent["params"] == {"filename": name}
