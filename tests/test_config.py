from __future__ import annotations

import json
from pathlib import Path

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
            keys="users",
            file="/secrets/test-secret.age",
        )
        assert secret.name == "test-secret"
        assert secret.keys == "users"
        assert secret.owner == "root"
        assert secret.group == "root"
        assert secret.mode == "0400"

    def test_key_groups_defaults(self):
        keys = KeyGroups()
        assert keys.systems == []
        assert keys.users == []
        assert keys.other == []
        assert keys.all == []

    def test_invalid_key_scope(self):
        with pytest.raises(ValueError):
            SecretDef(
                name="bad",
                keys="invalid_scope",
                file="/secrets/bad.age",
            )

    def test_missing_required_fields(self):
        with pytest.raises(ValueError):
            SecretDef.model_validate({})

    def test_sample_config_valid(self, sample_config: NixConfig):
        assert len(sample_config.secrets) == 2
        assert len(sample_config.keys.systems) == 1
        assert len(sample_config.keys.users) == 1
        assert len(sample_config.keys.all) == 2
        assert len(sample_config.identities) == 1
