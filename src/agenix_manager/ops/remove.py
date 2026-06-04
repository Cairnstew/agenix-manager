from __future__ import annotations

from pathlib import Path

from ..config import NixConfig
from .base import BaseOp


class RemoveOp(BaseOp):
    """File-level secret removal and orphan detection."""

    def remove_file(self, name: str) -> Path | None:
        age_path = Path(self.cfg.secrets_path) / f"{name}.age"
        if age_path.exists():
            age_path.unlink()
            return age_path
        return None

    def find_orphans(self) -> list[Path]:
        configured = {s.name for s in self.cfg.secrets}
        return sorted(
            f
            for f in Path(self.cfg.secrets_path).glob("*.age")
            if f.stem not in configured
        )


# ── module-level convenience API ──────────────────────────────────────

def remove_secret_file(cfg: NixConfig, name: str) -> Path | None:
    return RemoveOp(cfg).remove_file(name)


def find_orphaned_secrets(cfg: NixConfig) -> list[Path]:
    return RemoveOp(cfg).find_orphans()
