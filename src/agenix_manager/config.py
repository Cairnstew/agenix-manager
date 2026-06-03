from __future__ import annotations

import json
import socket
import subprocess
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class SecretDef(BaseModel):
    name: str
    keys: Literal["all", "systems", "users", "other"] = "all"
    owner: str = "root"
    group: str = "root"
    mode: str = "0400"
    file: str


class KeyGroups(BaseModel):
    systems: list[str] = Field(default_factory=list)
    users: list[str] = Field(default_factory=list)
    other: list[str] = Field(default_factory=list)
    all: list[str] = Field(default_factory=list)


class NixConfig(BaseModel):
    model_config = {"populate_by_name": True}
    secrets_path: str = Field(alias="secretsPath")
    flake_root: str = Field(alias="flakeRoot")
    identities: list[str]
    keys: KeyGroups
    secrets: list[SecretDef]


def load_from_nix_eval(host: str | None = None, flake_ref: str = ".") -> NixConfig:
    hostname = host or socket.gethostname()
    attr = f"{flake_ref}#nixosConfigurations.{hostname}.config.agenixManager.cliConfig"
    result = subprocess.run(
        ["nix", "eval", attr, "--json", "--impure"],
        capture_output=True,
        text=True,
        check=True,
    )
    return NixConfig.model_validate(json.loads(result.stdout))


def load_from_file(path: Path) -> NixConfig:
    return NixConfig.model_validate(json.loads(path.read_text()))
