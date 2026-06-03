from __future__ import annotations

import os
import subprocess
from pathlib import Path

from ..config import NixConfig, SecretDef


def encrypt_secret(cfg: NixConfig, secret: SecretDef) -> None:
    subprocess.run(
        ["agenix", "-e", f"{secret.name}.age"],
        cwd=cfg.secrets_path,
        check=True,
        env={
            **os.environ,
            "AGENIX_SECRETS": str(Path(cfg.secrets_path) / "secrets.nix"),
        },
    )
