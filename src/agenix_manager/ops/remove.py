from __future__ import annotations

from pathlib import Path

from ..config import NixConfig


def remove_secret_file(cfg: NixConfig, name: str) -> Path | None:
    age_path = Path(cfg.secrets_path) / f"{name}.age"
    if age_path.exists():
        age_path.unlink()
        return age_path
    return None


def find_orphaned_secrets(cfg: NixConfig) -> list[Path]:
    secrets_path = Path(cfg.secrets_path)
    configured_names = {s.name for s in cfg.secrets}
    return sorted(f for f in secrets_path.glob("*.age") if f.stem not in configured_names)
