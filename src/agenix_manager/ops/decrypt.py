from __future__ import annotations

from ..config import NixConfig, SecretDef
from .base import BaseOp


class DecryptOp(BaseOp):
    """Decrypt a secret to plaintext via ``age -d``."""

    def decrypt(self, secret: SecretDef, identity_path: str | None = None) -> str:
        identities = [identity_path] if identity_path else self.cfg.identities
        cmd = ["age", "-d"]
        for i in identities:
            cmd += ["-i", i]
        cmd.append(secret.file)
        result = self._run(cmd, capture_output=True)
        return result.stdout


# ── module-level convenience API ──────────────────────────────────────

def decrypt_secret(
    cfg: NixConfig, secret: SecretDef, identity_path: str | None = None
) -> str:
    return DecryptOp(cfg).decrypt(secret, identity_path)
