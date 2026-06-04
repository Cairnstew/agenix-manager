from __future__ import annotations

from ..config import NixConfig, SecretDef
from ..secrets_nix import write_secrets_nix
from .base import BaseOp
from .errors import AgenixOpError


class RekeyOp(BaseOp):
    """Re-encrypt one or more secrets with the current key set."""

    def rekey(self, secrets: list[SecretDef]) -> None:
        agenix = self._find_agenix()
        try:
            write_secrets_nix(self.cfg)
        except OSError as e:
            raise AgenixOpError(
                command="write_secrets_nix",
                stderr=str(e),
                returncode=1,
            ) from e
        names = [f"{s.name}.age" for s in secrets]
        self._run(
            [agenix, "--rekey"] + names,
            cwd=self.cfg.secrets_path,
            env=self._rules_env,
        )


# ── module-level convenience API ──────────────────────────────────────

def rekey_secrets(cfg: NixConfig, secrets: list[SecretDef]) -> None:
    RekeyOp(cfg).rekey(secrets)
