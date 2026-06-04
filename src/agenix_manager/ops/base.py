from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from ..config import NixConfig
from .errors import AgenixOpError

_AGENIX_CANDIDATES = [
    "/run/current-system/sw/bin/agenix",
    "/nix/var/nix/profiles/default/bin/agenix",
]

_AGE_CANDIDATES = [
    "/run/current-system/sw/bin/age",
    "/nix/var/nix/profiles/default/bin/age",
]


class BaseOp:
    """Shared infrastructure for all secret operations.

    Provides binary discovery, subprocess invocation with consistent
    error wrapping, and the RULES path helper used by agenix.
    """

    def __init__(self, cfg: NixConfig) -> None:
        self.cfg = cfg

    # ── binary discovery ──────────────────────────────────────────────

    def _find_agenix(self) -> str:
        if self.cfg.agenix_bin:
            return self.cfg.agenix_bin
        found = shutil.which("agenix")
        if found:
            return found
        for candidate in _AGENIX_CANDIDATES:
            if Path(candidate).exists():
                return candidate
        return "agenix"

    def _find_age(self) -> str:
        found = shutil.which("age")
        if found:
            return found
        for candidate in _AGE_CANDIDATES:
            if Path(candidate).exists():
                return candidate
        return "age"

    # ── subprocess helper ─────────────────────────────────────────────

    def _run(
        self, cmd: list[str], **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        """Run *cmd* and wrap any failure in ``AgenixOpError``."""
        try:
            result = subprocess.run(cmd, check=True, text=True, **kwargs)  # type: ignore[arg-type]
            return result  # type: ignore[return-value]
        except subprocess.CalledProcessError as e:
            raise AgenixOpError(
                command=" ".join(e.cmd),
                stderr=e.stderr or "",
                returncode=e.returncode,
            ) from e

    # ── RULES path for agenix ─────────────────────────────────────────

    @property
    def _rules_path(self) -> str:
        if self.cfg.secrets_nix_path:
            return self.cfg.secrets_nix_path
        return str(Path(self.cfg.secrets_path) / "secrets.nix")

    # ── RULES environment ─────────────────────────────────────────────

    @property
    def _rules_env(self) -> dict[str, str]:
        return {**os.environ, "RULES": self._rules_path}
