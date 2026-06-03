from __future__ import annotations

import subprocess

from ..config import NixConfig, SecretDef


def decrypt_secret(cfg: NixConfig, secret: SecretDef, identity_path: str | None = None) -> str:
    identities = [identity_path] if identity_path else cfg.identities
    cmd = ["age", "-d"]
    for i in identities:
        cmd += ["-i", i]
    cmd.append(secret.file)
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return result.stdout
