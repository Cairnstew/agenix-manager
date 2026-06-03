from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from agenix_manager.manifest import (
    Manifest,
    ManifestError,
    ManifestSecretEntry,
    add_secret,
    load_manifest,
    remove_secret,
    resolve_all,
    resolve_keys,
    resolve_secret_entry,
    save_manifest,
    find_manifest_path,
)
from agenix_manager.config import KeyGroups, SecretDef


class TestManifestSecretEntry:
    def test_valid_entry(self):
        entry = ManifestSecretEntry(name="my-secret", scope="users")
        assert entry.name == "my-secret"
        assert entry.scope == "users"
        assert entry.owner == "root"
        assert entry.group == "root"
        assert entry.mode == "0400"

    def test_invalid_name_rejected(self):
        with pytest.raises(Exception):
            ManifestSecretEntry(name="my secret with spaces")

    def test_invalid_mode_rejected(self):
        with pytest.raises(Exception):
            ManifestSecretEntry(name="test", scope="users", mode="07777")

    def test_scope_can_be_list(self):
        entry = ManifestSecretEntry(
            name="custom",
            scope=["ssh-ed25519 AAAA...key1", "ssh-ed25519 AAAA...key2"],
        )
        assert entry.scope == ["ssh-ed25519 AAAA...key1", "ssh-ed25519 AAAA...key2"]


class TestManifestModel:
    def test_valid_manifest(self):
        manifest = Manifest(version=1, secrets=[ManifestSecretEntry(name="t1")])
        assert manifest.version == 1
        assert len(manifest.secrets) == 1

    def test_unsupported_version(self):
        with pytest.raises(Exception, match="Unsupported manifest version"):
            Manifest(version=2, secrets=[])

    def test_default_version(self):
        manifest = Manifest(secrets=[])
        assert manifest.version == 1


class TestLoadManifest:
    def test_load_valid(self, tmp_path: Path):
        manifest_data = {
            "version": 1,
            "secrets": [
                {"name": "t1", "scope": "users"},
            ],
        }
        path = tmp_path / "secrets-manifest.json"
        path.write_text(json.dumps(manifest_data))
        manifest = load_manifest(path)
        assert manifest.version == 1
        assert len(manifest.secrets) == 1
        assert manifest.secrets[0].name == "t1"

    def test_load_invalid_json(self, tmp_path: Path):
        path = tmp_path / "bad.json"
        path.write_text("not json")
        with pytest.raises(ManifestError, match="Invalid JSON"):
            load_manifest(path)

    def test_load_not_an_object(self, tmp_path: Path):
        path = tmp_path / "bad.json"
        path.write_text(json.dumps([1, 2, 3]))
        with pytest.raises(ManifestError, match="must be a JSON object"):
            load_manifest(path)

    def test_load_unsupported_version(self, tmp_path: Path):
        manifest_data = {"version": 999, "secrets": []}
        path = tmp_path / "bad.json"
        path.write_text(json.dumps(manifest_data))
        with pytest.raises(ManifestError, match="Invalid manifest"):
            load_manifest(path)

    def test_load_missing_file(self):
        with pytest.raises(ManifestError, match="not found"):
            load_manifest(Path("/nonexistent/manifest.json"))


class TestSaveManifest:
    def test_save_and_reload(self, tmp_path: Path):
        path = tmp_path / "secrets-manifest.json"
        manifest = Manifest(secrets=[ManifestSecretEntry(name="t1")])
        save_manifest(path, manifest)
        assert path.exists()
        loaded = load_manifest(path)
        assert loaded.secrets[0].name == "t1"

    def test_save_is_atomic(self, tmp_path: Path):
        path = tmp_path / "secrets-manifest.json"
        manifest = Manifest(secrets=[ManifestSecretEntry(name="t1")])
        save_manifest(path, manifest)
        assert not path.with_suffix(".tmp").exists()
        assert path.exists()

    def test_save_preserves_all_fields(self, tmp_path: Path):
        path = tmp_path / "secrets-manifest.json"
        manifest = Manifest(
            secrets=[
                ManifestSecretEntry(
                    name="full",
                    scope="systems",
                    owner="alice",
                    group="users",
                    mode="0600",
                )
            ]
        )
        save_manifest(path, manifest)
        raw = json.loads(path.read_text())
        assert raw["secrets"][0]["name"] == "full"
        assert raw["secrets"][0]["scope"] == "systems"
        assert raw["secrets"][0]["owner"] == "alice"
        assert raw["secrets"][0]["group"] == "users"
        assert raw["secrets"][0]["mode"] == "0600"


class TestAddSecret:
    def test_add_to_empty(self):
        manifest = Manifest(secrets=[])
        manifest = add_secret(manifest, name="new-secret", scope="users")
        assert len(manifest.secrets) == 1
        assert manifest.secrets[0].name == "new-secret"

    def test_add_duplicate_rejected(self):
        manifest = Manifest(secrets=[ManifestSecretEntry(name="existing")])
        with pytest.raises(ManifestError, match="already exists"):
            add_secret(manifest, name="existing", scope="users")

    def test_add_preserves_existing(self):
        manifest = Manifest(secrets=[ManifestSecretEntry(name="a")])
        manifest = add_secret(manifest, name="b", scope="systems")
        assert len(manifest.secrets) == 2
        assert manifest.secrets[0].name == "a"
        assert manifest.secrets[1].name == "b"


class TestRemoveSecret:
    def test_remove_existing(self):
        manifest = Manifest(
            secrets=[
                ManifestSecretEntry(name="a"),
                ManifestSecretEntry(name="b"),
            ]
        )
        manifest = remove_secret(manifest, "a")
        assert len(manifest.secrets) == 1
        assert manifest.secrets[0].name == "b"

    def test_remove_missing(self):
        manifest = Manifest(secrets=[ManifestSecretEntry(name="a")])
        with pytest.raises(ManifestError, match="not found"):
            remove_secret(manifest, "nonexistent")


class TestResolveKeys:
    def test_literal_key_list(self):
        keys = resolve_keys(
            ["ssh-ed25519 AAAA...k1"],
            KeyGroups(systems=[], users=[], other=[]),
        )
        assert keys == ["ssh-ed25519 AAAA...k1"]

    def test_scope_name_systems(self):
        kg = KeyGroups(
            systems=["ssh-ed25519 AAAA...s1"],
            users=[],
            other=[],
        )
        keys = resolve_keys("systems", kg)
        assert keys == ["ssh-ed25519 AAAA...s1"]

    def test_scope_name_users(self):
        kg = KeyGroups(
            systems=[],
            users=["ssh-ed25519 AAAA...u1"],
            other=[],
        )
        keys = resolve_keys("users", kg)
        assert keys == ["ssh-ed25519 AAAA...u1"]

    def test_scope_name_all(self):
        kg = KeyGroups(
            systems=["ssh-ed25519 AAAA...s1"],
            users=["ssh-ed25519 AAAA...u1"],
            other=["ssh-ed25519 AAAA...o1"],
        )
        keys = resolve_keys("all", kg)
        assert len(keys) == 3
        assert "ssh-ed25519 AAAA...s1" in keys
        assert "ssh-ed25519 AAAA...u1" in keys
        assert "ssh-ed25519 AAAA...o1" in keys

    def test_custom_group(self):
        kg = KeyGroups.model_validate(
            {
                "systems": [],
                "users": [],
                "other": [],
                "deployment": ["ssh-ed25519 AAAA...ci"],
            }
        )
        keys = resolve_keys("deployment", kg)
        assert keys == ["ssh-ed25519 AAAA...ci"]

    def test_unknown_scope_raises(self):
        kg = KeyGroups(systems=[], users=[], other=[])
        with pytest.raises(ManifestError, match="Unknown key scope"):
            resolve_keys("nonexistent", kg)


class TestResolveSecretEntry:
    def test_resolve_scope_entry(self):
        kg = KeyGroups(systems=["ssh-ed25519 AAAA...s1"], users=[], other=[])
        entry = ManifestSecretEntry(name="t1", scope="systems")
        secret = resolve_secret_entry(entry, kg, "/secrets")
        assert isinstance(secret, SecretDef)
        assert secret.name == "t1"
        assert secret.keys == ["ssh-ed25519 AAAA...s1"]
        assert secret.scope == "systems"
        assert secret.file == "/secrets/t1.age"

    def test_resolve_literal_key_entry(self):
        kg = KeyGroups(systems=[], users=[], other=[])
        entry = ManifestSecretEntry(
            name="custom",
            scope=["ssh-ed25519 AAAA...k1"],
        )
        secret = resolve_secret_entry(entry, kg, "/secrets")
        assert secret.keys == ["ssh-ed25519 AAAA...k1"]
        assert secret.scope == "custom"


class TestResolveAll:
    def test_resolves_multiple(self):
        kg = KeyGroups(
            systems=["ssh-ed25519 AAAA...s1"],
            users=["ssh-ed25519 AAAA...u1"],
            other=[],
        )
        manifest = Manifest(
            secrets=[
                ManifestSecretEntry(name="a", scope="systems"),
                ManifestSecretEntry(name="b", scope="users"),
            ]
        )
        secrets = resolve_all(manifest, kg, "/secrets")
        assert len(secrets) == 2
        assert secrets[0].name == "a"
        assert secrets[0].keys == ["ssh-ed25519 AAAA...s1"]
        assert secrets[1].name == "b"
        assert secrets[1].keys == ["ssh-ed25519 AAAA...u1"]

    def test_empty_manifest(self):
        kg = KeyGroups(systems=[], users=[], other=[])
        manifest = Manifest(secrets=[])
        secrets = resolve_all(manifest, kg, "/secrets")
        assert secrets == []


class TestFindManifestPath:
    def test_find_manifest_path(self):
        path = find_manifest_path("/secrets")
        assert path == Path("/secrets/secrets-manifest.json")

    def test_find_manifest_path_from_path(self):
        path = find_manifest_path(Path("/custom/path"))
        assert path == Path("/custom/path/secrets-manifest.json")
