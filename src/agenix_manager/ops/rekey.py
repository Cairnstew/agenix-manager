from __future__ import annotations

import subprocess

from ..config import NixConfig, SecretDef
from ..secrets_nix import write_secrets_nix


def rekey_secrets(cfg: NixConfig, secrets: list[SecretDef]) -> None:
    write_secrets_nix(cfg)
    names = [f"{s.name}.age" for s in secrets]
    subprocess.run(
        ["agenix", "--rekey"] + names,
        cwd=cfg.secrets_path,
        check=True,
    )
