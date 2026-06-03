from __future__ import annotations

import subprocess
from pathlib import Path

from ..config import NixConfig, SecretDef
from .errors import AgenixOpError


def encrypt_secret(cfg: NixConfig, secret: SecretDef) -> None:
    rules = str(Path(cfg.secrets_path) / "secrets.nix")
    try:
        subprocess.run(
            ["agenix", "-e", f"{secret.name}.age", "-r", rules],
            cwd=cfg.secrets_path,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        raise AgenixOpError(
            command=" ".join(e.cmd),
            stderr=e.stderr or "",
            returncode=e.returncode,
        ) from e
