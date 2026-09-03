from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from market_intel.foundation import fno_locator_binding as binding
from market_intel.foundation import fno_production_boundary as boundary


COMMIT = "a" * 40


def _database(path: Path, size: int = 8192) -> Path:
    payload = binding.SQLITE_MAGIC + b"\x00" * (binding.HEADER_BYTES - len(binding.SQLITE_MAGIC))
    path.write_bytes(payload + bytes((index % 251 for index in range(size - len(payload)))))
    return path


def _config(path: Path, target: Path, *, quote: str = "'") -> Path:
    path.write_text(
        "[unrelated]\nsecret = 'do-not-parse'\n[paths]\n"
        f"fno_db = {quote}{target}{quote}\nother = 'ignored'\n",
        encoding="utf-8",
    )
    return path


def test_locator_parses_only_approved_key_and_hashes_full_config(tmp_path):
    target = _database(tmp_path / "target.bin")
    config = _config(tmp_path / "config.toml", target)
    result = binding.prepare_synthetic_binding(config_path=config, source_commit=COMMIT)
    anchor = result.tracked_anchor
    assert anchor["configuration_key"] == "paths.fno_db"
    assert anchor["configuration_file_sha256"] == binding.sha256_bytes(config.read_bytes())
    assert "do-not-parse" not in json.dumps(result.tracked_anchor)


@pytest.mark.parametrize(
    ("contents", "decision"),
    [
        ("[paths]\n", binding.NOT_LOCATED),
        ("[paths]\nfno_db = ''\n", binding.NOT_LOCATED),
        ("[paths]\nfno_db = 'a'\nfno_db = 'b'\n", binding.NOT_LOCATED),
    ],
)
def test_missing_empty_or_ambiguous_locator_fails_closed(tmp_path, contents, decision):
    config = tmp_path / "config.toml"
    config.write_text(contents, encoding="utf-8")
    with pytest.raises(binding.LocatorBindingError) as exc:
        binding.prepare_synthetic_binding(config_path=config, source_commit=COMMIT)
    assert exc.value.decision == decision
    assert str(tmp_path) not in str(exc.value)


def test_missing_target_and_directory_fail_without_path_disclosure(tmp_path):
    for target, expected in ((tmp_path / "missing", binding.NOT_LOCATED),
                             (tmp_path / "directory", binding.NOT_SAFE)):
        if target.name == "directory":
            target.mkdir()
        config = _config(tmp_path / f"{target.name}.toml", target)
        with pytest.raises(binding.LocatorBindingError) as exc:
            binding.prepare_synthetic_binding(config_path=config, source_commit=COMMIT)
        assert exc.value.decision == expected
        assert str(target) not in str(exc.value)


def test_symlink_target_is_rejected_where_supported(tmp_path):
    target = _database(tmp_path / "target.bin")
    link = tmp_path / "link.bin"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("symlink creation unavailable")
    config = _config(tmp_path / "config.toml", link)
    with pytest.raises(binding.LocatorBindingError) as exc:
        binding.prepare_synthetic_binding(config_path=config, source_commit=COMMIT)
    assert exc.value.decision == binding.NOT_SAFE


def test_reparse_status_is_rejected(monkeypatch, tmp_path):
    target = _database(tmp_path / "target.bin")
    config = _config(tmp_path / "config.toml", target)
    monkeypatch.setattr(binding, "_is_reparse", lambda info: True)
    with pytest.raises(binding.LocatorBindingError) as exc:
        binding.prepare_synthetic_binding(config_path=config, source_commit=COMMIT)
    assert exc.value.decision == binding.NOT_SAFE


@pytest.mark.parametrize("payload", [b"", b"short", b"not sqlite" + b"x" * 100])
def test_short_or_invalid_header_fails_closed(tmp_path, payload):
    target = tmp_path / "target.bin"
    target.write_bytes(payload)
    config = _config(tmp_path / "config.toml", target)
    with pytest.raises(binding.LocatorBindingError) as exc:
        binding.prepare_synthetic_binding(config_path=config, source_commit=COMMIT)
    assert exc.value.decision == binding.HEADER_INVALID


def test_sample_offsets_are_deterministic_and_deduplicate_small_files():
    assert binding.sample_offsets(100) == (0,)
    first = binding.sample_offsets(binding.CHUNK_SIZE + 31)
    assert first == binding.sample_offsets(binding.CHUNK_SIZE + 31)
    assert first[0] == 0 and first[-1] == 31
    assert len(first) == len(set(first)) <= binding.NOMINAL_SAMPLE_COUNT


def test_large_offsets_include_first_last_and_62_interior_positions():
    size = binding.CHUNK_SIZE * 100
    offsets = binding.sample_offsets(size)
    assert len(offsets) == 64
    assert offsets[0] == 0
    assert offsets[-1] == size - binding.CHUNK_SIZE
    assert len(offsets[1:-1]) == 62


def test_sampled_root_is_ordered_and_reproducible():
    records = (
        binding.SampleRecord(5, 2, "b" * 64),
        binding.SampleRecord(0, 3, "a" * 64),
    )
    assert binding.sampled_identity_root(records) == binding.sampled_identity_root(
        tuple(reversed(records))
    )


def test_single_pass_budget_and_explicit_nonactivation_state(tmp_path):
    target = _database(tmp_path / "target.bin", binding.CHUNK_SIZE + 1000)
    config = _config(tmp_path / "config.toml", target)
    result = binding.prepare_synthetic_binding(config_path=config, source_commit=COMMIT)
    sampled = result.tracked_anchor["sampled_identity"]
    assert sampled["sample_pass_count"] == 1
    assert sampled["total_raw_bytes_read"] == sampled["sampled_bytes"] + 100
    assert sampled["total_raw_bytes_read"] <= binding.MAXIMUM_TOTAL_BYTES_READ
    assert sampled["full_file_hash"] is False
    assert result.tracked_anchor["production_activation_eligible"] is False


def test_read_budget_is_strict(monkeypatch, tmp_path):
    target = _database(tmp_path / "target.bin")
    with target.open("rb") as stream:
        with pytest.raises(binding.LocatorBindingError) as exc:
            binding._read_bounded(stream, 0, 1, [binding.MAXIMUM_TOTAL_BYTES_READ])
    assert exc.value.decision == binding.SCOPE_VIOLATION


def test_mutation_after_sample_fails_without_retry(tmp_path):
    target = _database(tmp_path / "target.bin")
    config = _config(tmp_path / "config.toml", target)
    calls = {"count": 0}

    def mutate():
        calls["count"] += 1
        with target.open("r+b") as stream:
            stream.seek(50)
            stream.write(b"changed")
            stream.flush()
            os.fsync(stream.fileno())

    with pytest.raises(binding.LocatorBindingError) as exc:
        binding.prepare_synthetic_binding(
            config_path=config, source_commit=COMMIT, mutation_hook=mutate
        )
    assert exc.value.decision == binding.CHANGED
    assert calls["count"] == 1


def test_tracked_artifacts_are_deterministic_and_private_path_is_separate(tmp_path):
    target = _database(tmp_path / "private-machine-name.bin")
    config = _config(tmp_path / "config.toml", target)
    one = binding.prepare_synthetic_binding(config_path=config, source_commit=COMMIT)
    two = binding.prepare_synthetic_binding(config_path=config, source_commit=COMMIT)
    assert binding.canonical_json_bytes(one.tracked_anchor) == binding.canonical_json_bytes(
        two.tracked_anchor
    )
    assert binding.canonical_json_bytes(one.binding_proposal) == binding.canonical_json_bytes(
        two.binding_proposal
    )
    tracked = json.dumps({"anchor": one.tracked_anchor, "proposal": one.binding_proposal})
    assert str(target) not in tracked and str(tmp_path) not in tracked
    assert one.private_result["resolved_path"] == str(target.resolve())


def test_artifact_writes_are_immutable_and_cleanup_partial_publication(tmp_path):
    target = _database(tmp_path / "target.bin")
    config = _config(tmp_path / "config.toml", target)
    result = binding.prepare_synthetic_binding(config_path=config, source_commit=COMMIT)
    private = tmp_path / "ignored/private.json"
    anchor = tmp_path / "tracked/anchor.json"
    proposal = tmp_path / "tracked/proposal.json"
    hashes = binding.write_binding_artifacts(
        result, private_path=private, anchor_path=anchor, proposal_path=proposal
    )
    assert set(hashes) == {"private_sha256", "anchor_sha256", "proposal_sha256"}
    with pytest.raises(binding.LocatorBindingError):
        binding.write_binding_artifacts(
            result, private_path=private, anchor_path=anchor, proposal_path=proposal
        )


def test_private_runtime_artifact_location_is_git_ignored():
    gitignore = (Path(__file__).parents[1] / ".gitignore").read_text(encoding="utf-8")
    assert "artifacts/" in gitignore


def test_entrypoint_delta_is_exact_and_nonactivating():
    root = Path(__file__).parents[1]
    delta = json.loads(
        (root / "specs/research_r9f_entrypoint_delta_v1.json").read_text(encoding="utf-8")
    )
    assert delta["unsafe_bypass_count"] == 0
    assert delta["removed_entrypoints"] == []
    assert len(delta["added_executable_entrypoints"]) == 1
    entry = delta["added_executable_entrypoints"][0]
    assert entry["path"] == "tools/prepare_fno_locator_binding.py"
    assert all(entry[key] is False for key in (
        "database_connection", "sql", "network", "market_rows", "audit", "activation"
    ))


def test_implementation_has_no_sqlite_network_market_or_broker_path():
    source = Path(binding.__file__).read_text(encoding="utf-8")
    tool = (Path(__file__).parents[1] / "tools/prepare_fno_locator_binding.py").read_text(
        encoding="utf-8"
    )
    prohibited = (
        "import sqlite3", "from sqlite3", "sqlite3.connect", "import requests",
        "import httpx", "import urllib", "kite_connect",
        "execute_approved_stage_1_3_audit",
    )
    for token in prohibited:
        assert token not in source.lower()
        assert token not in tool.lower()


def test_existing_production_interlock_remains_impossible():
    result = boundary.evaluate_production_interlocks(
        boundary.ProductionInterlockEvidence(**{
            field: True
            for field in boundary.ProductionInterlockEvidence.__dataclass_fields__
        })
    )
    assert result["permitted"] is False
    assert binding.PRODUCTION_INTERLOCK == boundary.DELIBERATE_INTERLOCK
    assert result["database_access_authorized"] is False
    assert result["audit_execution_authorized"] is False
