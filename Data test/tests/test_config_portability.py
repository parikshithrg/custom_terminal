from __future__ import annotations

from pathlib import Path

import pytest

from dtest.config import PATH_ENV_VARS, load_config


def test_machine_paths_can_all_be_bound_without_editing_tracked_config(monkeypatch, tmp_path: Path):
    expected = {}
    for key, variable in PATH_ENV_VARS.items():
        value = tmp_path / key
        monkeypatch.setenv(variable, str(value))
        expected[key] = value

    paths = load_config().paths

    for key, value in expected.items():
        assert getattr(paths, key) == value


def test_empty_machine_binding_fails_closed(monkeypatch):
    monkeypatch.setenv("DTEST_PRICE_DIR", "")
    with pytest.raises(ValueError, match="DTEST_PRICE_DIR is set but empty"):
        load_config()
