from __future__ import annotations

import subprocess

from ..config import NixConfig, SecretDef
from ..secrets_nix import write_secrets_nix
from .errors import AgenixOpError


def rekey_secrets(cfg: NixConfig, secrets: list[SecretDef]) -> None:
    try:
        write_secrets_nix(cfg)
    except OSError as e:
        raise AgenixOpError(
            command="write_secrets_nix",
            stderr=str(e),
            returncode=1,
        ) from e
    names = [f"{s.name}.age" for s in secrets]
    try:
        subprocess.run(
            ["agenix", "--rekey"] + names,
            cwd=cfg.secrets_path,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        raise AgenixOpError(
            command=" ".join(e.cmd),
            stderr=e.stderr or "",
            returncode=e.returncode,
        ) from e
