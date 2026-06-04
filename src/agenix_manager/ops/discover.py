from __future__ import annotations

from pathlib import Path

from ..config import NixConfig
from .base import BaseOp


class DiscoverOp(BaseOp):
    """Find .age files on disk that are not yet tracked in the manifest."""

    def find_untracked(self) -> list[Path]:
        configured = {s.name for s in self.cfg.secrets}
        return sorted(
            f
            for f in Path(self.cfg.secrets_path).glob("*.age")
            if f.stem not in configured
        )


def find_untracked_secrets(cfg: NixConfig) -> list[Path]:
    return DiscoverOp(cfg).find_untracked()
