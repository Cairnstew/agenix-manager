from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import NixConfig, SecretDef


@dataclass
class SecretStatus:
    definition: SecretDef
    age_file_exists: bool
    age_file_path: Path


def compute_state(cfg: NixConfig) -> list[SecretStatus]:
    secrets_path = Path(cfg.secrets_path)
    statuses = []
    for secret in cfg.secrets:
        age_path = secrets_path / f"{secret.name}.age"
        statuses.append(
            SecretStatus(
                definition=secret,
                age_file_exists=age_path.exists(),
                age_file_path=age_path,
            )
        )
    return statuses


def missing_secrets(cfg: NixConfig) -> list[SecretDef]:
    return [s.definition for s in compute_state(cfg) if not s.age_file_exists]


def present_secrets(cfg: NixConfig) -> list[SecretDef]:
    return [s.definition for s in compute_state(cfg) if s.age_file_exists]
