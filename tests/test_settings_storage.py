import json
import os
from unittest.mock import patch

import pytest

from app.core import settings_storage


def test_settings_round_trip_and_invalid_root(tmp_path):
    path = tmp_path / "settings.json"
    assert settings_storage.read_settings(str(path)) is None
    settings_storage.write_settings(str(path), {"theme": "тёмная"})
    assert settings_storage.read_settings(str(path)) == {"theme": "тёмная"}
    path.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError):
        settings_storage.read_settings(str(path))
    path.write_text("{", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        settings_storage.read_settings(str(path))


def test_failed_settings_publication_keeps_original_and_cleans_temp(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text('{"old": true}', encoding="utf-8")
    with patch.object(settings_storage.os, "replace", side_effect=PermissionError("denied")):
        with pytest.raises(PermissionError):
            settings_storage.write_settings(str(path), {"new": True})
    assert json.loads(path.read_text(encoding="utf-8")) == {"old": True}
    assert list(tmp_path.iterdir()) == [path]


def test_migration_selects_newest_and_does_not_overwrite_newer_target(tmp_path):
    older, newer, target = [tmp_path / name for name in ("old.json", "new.json", "target.json")]
    older.write_text('{"version": 1}', encoding="utf-8")
    newer.write_text('{"version": 2}', encoding="utf-8")
    os.utime(older, (100, 100))
    os.utime(newer, (200, 200))
    with patch.object(settings_storage, "_legacy_settings_candidates", return_value=(str(older), str(newer))):
        settings_storage._migrate_legacy_settings(str(target))
        assert json.loads(target.read_text(encoding="utf-8")) == {"version": 2}
        target.write_text('{"version": 3}', encoding="utf-8")
        os.utime(target, (300, 300))
        settings_storage._migrate_legacy_settings(str(target))
    assert json.loads(target.read_text(encoding="utf-8")) == {"version": 3}
