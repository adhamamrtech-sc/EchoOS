"""Safety test: actions must never use sudo or a shell string."""
from pathlib import Path


def test_actions_never_use_sudo_or_shell():
    for path in Path("actions").glob("*.py"):
        code = path.read_text()
        assert '"sudo"' not in code, f"sudo found in {path}"
        assert "shell=True" not in code, f"shell=True found in {path}"
