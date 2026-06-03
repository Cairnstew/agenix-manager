from __future__ import annotations

import json
import os
from pathlib import Path

from pydantic import BaseModel, field_validator

from .config import KeyGroups, SecretDef


class ManifestError(Exception):
    pass


class ManifestSecretEntry(BaseModel):
    name: str
    scope: str | list[str] = "all"
    owner: str = "root"
    group: str = "root"
    mode: str = "0400"

    @field_validator("name")
    @classmethod
    def _validate_name(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Secret name cannot be empty")
        import re

        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError(
                "Secret name must be alphanumeric with hyphens/underscores only, no spaces"
            )
        return v.strip()

    @field_validator("mode")
    @classmethod
    def _validate_mode(cls, v: str) -> str:
        if not v.startswith("0") or len(v) != 4 or not v.isdigit():
            raise ValueError("Mode must be a 4-digit octal string (e.g. 0400)")
        return v


class Manifest(BaseModel):
    version: int = 1
    secrets: list[ManifestSecretEntry] = []

    @field_validator("version")
    @classmethod
    def _validate_version(cls, v: int) -> int:
        if v != 1:
            raise ValueError(f"Unsupported manifest version: {v}. Expected 1.")
        return v


def resolve_keys(scope: str | list[str], key_groups: KeyGroups) -> list[str]:
    if isinstance(scope, list):
        known = {"all", "systems", "users", "other"} | set(key_groups.model_extra or {})
        if all(s in known for s in scope):
            result: list[str] = []
            for s in scope:
                if s == "all":
                    result.extend(key_groups.systems + key_groups.users + key_groups.other)
                else:
                    result.extend(getattr(key_groups, s))
            return result
        return scope
    if scope == "all":
        return key_groups.systems + key_groups.users + key_groups.other
    try:
        return getattr(key_groups, scope)  # type: ignore[no-any-return]
    except AttributeError:
        raise ManifestError(f"Unknown key scope '{scope}'")


def resolve_secret_entry(
    entry: ManifestSecretEntry, key_groups: KeyGroups, secrets_path: str
) -> SecretDef:
    keys = resolve_keys(entry.scope, key_groups)
    scope_str = entry.scope if isinstance(entry.scope, str) else "custom"
    return SecretDef(
        name=entry.name,
        keys=keys,
        scope=scope_str,
        owner=entry.owner,
        group=entry.group,
        mode=entry.mode,
        file=f"{secrets_path}/{entry.name}.age",
    )


def resolve_all(manifest: Manifest, key_groups: KeyGroups, secrets_path: str) -> list[SecretDef]:
    return [resolve_secret_entry(e, key_groups, secrets_path) for e in manifest.secrets]


def load_manifest(path: Path) -> Manifest:
    try:
        raw = json.loads(path.read_text())
    except FileNotFoundError:
        raise ManifestError(f"Manifest file not found: {path}")
    except json.JSONDecodeError as e:
        raise ManifestError(f"Invalid JSON in manifest file {path}: {e}")
    if not isinstance(raw, dict):
        raise ManifestError(f"Manifest must be a JSON object, got {type(raw).__name__}")
    try:
        return Manifest.model_validate(raw)
    except Exception as e:
        raise ManifestError(f"Invalid manifest format: {e}")


def save_manifest(path: Path, manifest: Manifest) -> None:
    tmp = path.with_suffix(".tmp")
    try:
        tmp.write_text(manifest.model_dump_json(indent=2) + "\n")
        tmp.chmod(0o644)
        os.replace(tmp, path)
    except OSError as e:
        raise ManifestError(f"Failed to write manifest to {path}: {e}")


def add_secret(
    manifest: Manifest,
    name: str,
    scope: str | list[str] = "all",
    owner: str = "root",
    group: str = "root",
    mode: str = "0400",
) -> Manifest:
    if any(s.name == name for s in manifest.secrets):
        raise ManifestError(f"Secret '{name}' already exists in manifest")
    entry = ManifestSecretEntry(name=name, scope=scope, owner=owner, group=group, mode=mode)
    return Manifest(version=manifest.version, secrets=[*manifest.secrets, entry])


def remove_secret(manifest: Manifest, name: str) -> Manifest:
    new_secrets = [s for s in manifest.secrets if s.name != name]
    if len(new_secrets) == len(manifest.secrets):
        raise ManifestError(f"Secret '{name}' not found in manifest")
    return Manifest(version=manifest.version, secrets=new_secrets)


def find_manifest_path(cfg_secrets_path: str | Path) -> Path:
    return Path(cfg_secrets_path) / "secrets-manifest.json"
