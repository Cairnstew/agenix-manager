from __future__ import annotations

from pathlib import Path

from ..config import NixConfig, SecretDef
from .base import BaseOp


class EncryptOp(BaseOp):
    """Encrypt (create / re-encrypt) a secret.

    Two code paths:
    * ``encrypt`` — launches ``$EDITOR`` via ``agenix -e``.
    * ``encrypt_from_stdin`` — pipes plaintext directly to ``age -e -a``.
    """

    def encrypt(self, secret: SecretDef) -> None:
        agenix = self._find_agenix()
        self._run(
            [agenix, "-e", f"{secret.name}.age"],
            cwd=self.cfg.secrets_path,
            env=self._rules_env,
        )

    def encrypt_from_stdin(self, secret: SecretDef, plaintext: str) -> None:
        age = self._find_age()
        out = Path(self.cfg.secrets_path) / f"{secret.name}.age"
        cmd = [age, "-e", "-a"]
        for key in secret.keys:
            cmd += ["-r", key]
        cmd += ["-o", str(out)]
        self._run(cmd, input=plaintext)


# ── module-level convenience API ──────────────────────────────────────

def encrypt_secret(cfg: NixConfig, secret: SecretDef) -> None:
    EncryptOp(cfg).encrypt(secret)


def encrypt_secret_from_stdin(cfg: NixConfig, secret: SecretDef, plaintext: str) -> None:
    EncryptOp(cfg).encrypt_from_stdin(secret, plaintext)
