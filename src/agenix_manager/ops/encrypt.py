from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from ..config import NixConfig, SecretDef
from .errors import AgenixOpError


def _find_agenix() -> str:
    agenix = shutil.which("agenix")
    if agenix:
        return agenix
    for candidate in [
        "/run/current-system/sw/bin/agenix",
        "/nix/var/nix/profiles/default/bin/agenix",
    ]:
        if Path(candidate).exists():
            return candidate
    return "agenix"


def encrypt_secret(cfg: NixConfig, secret: SecretDef) -> None:
    agenix_bin = _find_agenix()
    rules = str(Path(cfg.secrets_path) / "secrets.nix")
    try:
        subprocess.run(
            [agenix_bin, "-e", f"{secret.name}.age", "-r", rules],
            cwd=cfg.secrets_path,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        raise AgenixOpError(
            command=" ".join(e.cmd),
            stderr=e.stderr or "",
            returncode=e.returncode,
        ) from e


def _find_age() -> str:
    age = shutil.which("age")
    if age:
        return age
    for candidate in [
        "/run/current-system/sw/bin/age",
        "/nix/var/nix/profiles/default/bin/age",
    ]:
        if Path(candidate).exists():
            return candidate
    return "age"


def encrypt_secret_from_stdin(cfg: NixConfig, secret: SecretDef, plaintext: str) -> None:
    age_bin = _find_age()
    out_path = Path(cfg.secrets_path) / f"{secret.name}.age"
    cmd = [age_bin, "-e", "-a"]
    for key in secret.keys:
        cmd += ["-r", key]
    cmd += ["-o", str(out_path)]
    try:
        subprocess.run(cmd, input=plaintext, text=True, check=True)
    except subprocess.CalledProcessError as e:
        raise AgenixOpError(
            command=" ".join(e.cmd),
            stderr=e.stderr or "",
            returncode=e.returncode,
        ) from e
