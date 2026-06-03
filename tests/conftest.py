from __future__ import annotations

from pathlib import Path

import pytest

from agenix_manager.config import NixConfig


@pytest.fixture
def sample_config_dict() -> dict:
    return {
        "secrets_path": "/tmp/agenix-test-secrets",
        "identities": ["/etc/ssh/ssh_host_ed25519_key"],
        "keys": {
            "systems": ["ssh-ed25519 AAAA...systemkey"],
            "users": ["ssh-ed25519 AAAA...userkey"],
            "other": [],
            "all": [
                "ssh-ed25519 AAAA...systemkey",
                "ssh-ed25519 AAAA...userkey",
            ],
        },
        "secrets": [
            {
                "name": "github-token",
                "keys": ["ssh-ed25519 AAAA...userkey"],
                "scope": "users",
                "owner": "root",
                "group": "root",
                "mode": "0400",
                "file": "/tmp/agenix-test-secrets/github-token.age",
            },
            {
                "name": "db-password",
                "keys": [
                    "ssh-ed25519 AAAA...systemkey",
                    "ssh-ed25519 AAAA...userkey",
                ],
                "scope": "all",
                "owner": "postgres",
                "group": "postgres",
                "mode": "0400",
                "file": "/tmp/agenix-test-secrets/db-password.age",
            },
        ],
    }


@pytest.fixture
def sample_config(sample_config_dict: dict) -> NixConfig:
    return NixConfig.model_validate(sample_config_dict)


@pytest.fixture
def secrets_dir(tmp_path: Path) -> Path:
    d = tmp_path / "secrets"
    d.mkdir()
    return d


@pytest.fixture
def sample_config_with_tmp(sample_config_dict: dict, secrets_dir: Path) -> NixConfig:
    sample_config_dict["secrets_path"] = str(secrets_dir)
    for secret in sample_config_dict["secrets"]:
        secret["file"] = str(secrets_dir / f"{secret['name']}.age")
    return NixConfig.model_validate(sample_config_dict)
