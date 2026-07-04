from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).with_name("zk_cli.py")
spec = importlib.util.spec_from_file_location("zk_cli", SCRIPT)
assert spec is not None
zk_cli = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(zk_cli)


def test_capture_updates_today_journal_and_related_note(tmp_path: Path) -> None:
    result = zk_cli.capture_note(
        notebook_dir=tmp_path,
        title="Fix backup alert",
        details="Snapshot failed on pve. Check the PBS job.",
        related_note="home-server",
        capture_date="2026-05-10",
    )

    journal = tmp_path / "journal" / "2026-05-10.md"
    related = tmp_path / "home-server.md"

    assert result.journal == journal
    assert result.related == related
    assert "- [[home-server]] Fix backup alert" in journal.read_text()
    assert "  Snapshot failed on pve. Check the PBS job." in journal.read_text()
    assert "- [[journal/2026-05-10]] Fix backup alert" in related.read_text()
    assert "  Snapshot failed on pve. Check the PBS job." in related.read_text()


def test_capture_appends_inside_existing_notes_section(tmp_path: Path) -> None:
    journal = tmp_path / "journal" / "2026-05-10.md"
    journal.parent.mkdir()
    journal.write_text("# 2026-05-10\n\n## Notes\n- existing\n\n## Later\nkeep\n")
    related = tmp_path / "home-server.md"
    related.write_text("# Home Server\n\n## Notes\n- existing related\n\n## Links\nkeep\n")

    zk_cli.capture_note(
        notebook_dir=tmp_path,
        title="Rotate credentials",
        details="Update the env file after rotation.",
        related_note="home-server",
        capture_date="2026-05-10",
    )

    assert journal.read_text() == (
        "# 2026-05-10\n\n"
        "## Notes\n"
        "- existing\n"
        "- [[home-server]] Rotate credentials\n"
        "  Update the env file after rotation.\n\n"
        "## Later\n"
        "keep\n"
    )
    assert related.read_text() == (
        "# Home Server\n\n"
        "## Notes\n"
        "- existing related\n"
        "- [[journal/2026-05-10]] Rotate credentials\n"
        "  Update the env file after rotation.\n\n"
        "## Links\n"
        "keep\n"
    )


def test_capture_slugs_new_related_note_from_title(tmp_path: Path) -> None:
    result = zk_cli.capture_note(
        notebook_dir=tmp_path,
        title="Tune card layout",
        details="Preserve mobile density.",
        related_note="Home Assistant UI",
        capture_date="2026-05-10",
    )

    assert result.related == tmp_path / "home-assistant-ui.md"
    assert "# Home Assistant UI" in result.related.read_text()
    assert "- [[home-assistant-ui]] Tune card layout" in result.journal.read_text()
