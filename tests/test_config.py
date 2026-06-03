from __future__ import annotations

import json
from pathlib import Path

import pytest

import pytest

from agenix_manager.config import (
    KeyGroups,
    NixConfig,
    SecretDef,
    load_from_file,
)


class TestNixConfig:
    def test_load_from_file(self, sample_config_dict: dict, tmp_path: Path):
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(sample_config_dict))

        cfg = load_from_file(config_file)
        assert isinstance(cfg, NixConfig)
        assert cfg.secrets_path == "/tmp/agenix-test-secrets"
        assert len(cfg.secrets) == 2

    def test_secret_def_fields(self):
        secret = SecretDef(
            name="test-secret",
            keys=["ssh-ed25519 AAAA...u"],
            file="/secrets/test-secret.age",
        )
        assert secret.name == "test-secret"
        assert secret.keys == ["ssh-ed25519 AAAA...u"]
        assert secret.scope == "all"
        assert secret.owner == "root"
        assert secret.group == "root"
        assert secret.mode == "0400"

    def test_key_groups_defaults(self):
        keys = KeyGroups()
        assert keys.systems == []
        assert keys.users == []
        assert keys.other == []

    def test_key_groups_custom_group(self):
        data = {
            "systems": ["ssh-ed25519 AAAA...s"],
            "users": [],
            "other": [],
            "deployment": ["ssh-ed25519 AAAA...ci"],
        }
        keys = KeyGroups.model_validate(data)
        assert keys.systems == ["ssh-ed25519 AAAA...s"]
        assert keys.deployment == ["ssh-ed25519 AAAA...ci"]

    def test_missing_required_fields(self):
        with pytest.raises(ValueError):
            SecretDef.model_validate({})

    def test_sample_config_valid(self, sample_config: NixConfig):
        assert len(sample_config.secrets) == 2
        assert len(sample_config.keys.systems) == 1
        assert len(sample_config.keys.users) == 1
        assert len(sample_config.identities) == 1

    def test_empty_keys_list_rejected(self):
        data = {
            "secrets_path": "/tmp/test",
            "identities": [],
            "keys": {"systems": [], "users": [], "other": [], "all": []},
            "secrets": [{"name": "bad", "keys": [], "file": "/tmp/test/bad.age"}],
        }
        with pytest.raises(ValueError, match="empty key list"):
            NixConfig.model_validate(data)

    def test_scope_default_is_all(self, sample_config: NixConfig):
        assert sample_config.secrets[0].scope == "users"
        assert sample_config.secrets[1].scope == "all"
        default = SecretDef(name="x", keys=["k"], file="/x.age")
        assert default.scope == "all"
