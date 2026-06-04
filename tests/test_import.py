from __future__ import annotations

from pathlib import Path

from agenix_manager.config import NixConfig
from agenix_manager.ops.discover import find_untracked_secrets


def _empty_cfg(secrets_dir: Path) -> NixConfig:
    return NixConfig.model_validate({
        "secrets_path": str(secrets_dir),
        "identities": ["/etc/ssh/ssh_host_ed25519_key"],
        "keys": {
            "systems": ["ssh-ed25519 AAAA...systemkey"],
            "users": ["ssh-ed25519 AAAA...userkey"],
            "other": [],
            "all": ["ssh-ed25519 AAAA...systemkey", "ssh-ed25519 AAAA...userkey"],
        },
        "secrets": [],
    })


def _cfg_with_one_tracked(secrets_dir: Path) -> NixConfig:
    return NixConfig.model_validate({
        "secrets_path": str(secrets_dir),
        "identities": ["/etc/ssh/ssh_host_ed25519_key"],
        "keys": {
            "systems": ["ssh-ed25519 AAAA...systemkey"],
            "users": ["ssh-ed25519 AAAA...userkey"],
            "other": [],
            "all": ["ssh-ed25519 AAAA...systemkey", "ssh-ed25519 AAAA...userkey"],
        },
        "secrets": [
            {
                "name": "tracked-secret",
                "keys": ["ssh-ed25519 AAAA...systemkey"],
                "scope": "systems",
                "owner": "root",
                "group": "root",
                "mode": "0400",
                "file": str(secrets_dir / "tracked-secret.age"),
            },
        ],
    })


class TestDiscoverOp:
    def test_find_untracked_none(self, secrets_dir: Path) -> None:
        cfg = _empty_cfg(secrets_dir)
        result = find_untracked_secrets(cfg)
        assert result == []

    def test_find_untracked_with_extra(self, secrets_dir: Path) -> None:
        cfg = _empty_cfg(secrets_dir)
        extra = secrets_dir / "extra.age"
        extra.write_text("encrypted-content")
        result = find_untracked_secrets(cfg)
        assert result == [extra]

    def test_find_untracked_multiple(self, secrets_dir: Path) -> None:
        cfg = _empty_cfg(secrets_dir)
        (secrets_dir / "extra1.age").write_text("x")
        (secrets_dir / "extra2.age").write_text("x")
        (secrets_dir / "extra3.age").write_text("x")
        result = find_untracked_secrets(cfg)
        assert len(result) == 3

    def test_find_untracked_ignores_non_age(self, secrets_dir: Path) -> None:
        cfg = _empty_cfg(secrets_dir)
        (secrets_dir / "not-a-secret.txt").write_text("plaintext")
        with_age = secrets_dir / "real.age"
        with_age.write_text("ciphertext")
        result = find_untracked_secrets(cfg)
        assert result == [with_age]

    def test_find_untracked_ignores_tracked(self, secrets_dir: Path) -> None:
        cfg = _cfg_with_one_tracked(secrets_dir)
        (secrets_dir / "tracked-secret.age").write_text("tracked")
        extra = secrets_dir / "extra.age"
        extra.write_text("x")
        result = find_untracked_secrets(cfg)
        assert result == [extra]

    def test_find_untracked_empty_dir(self, secrets_dir: Path) -> None:
        cfg = _empty_cfg(secrets_dir)
        result = find_untracked_secrets(cfg)
        assert result == []
