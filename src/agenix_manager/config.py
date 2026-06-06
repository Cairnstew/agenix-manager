from __future__ import annotations

import json
import socket
import subprocess
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .ops.errors import AgenixOpError


class SecretDef(BaseModel):
    name: str
    keys: list[str] = Field(default_factory=lambda: ["all"])
    scope: str = "all"
    owner: str = "root"
    group: str = "root"
    mode: str = "0400"
    file: str


class KeyGroups(BaseModel):
    model_config = ConfigDict(extra="allow")

    def __getattr__(self, name: str) -> list[str]:
        extra = self.__pydantic_extra__ or {}
        if name in extra:
            return extra[name]  # type: ignore[no-any-return]
        msg = f"'{type(self).__name__}' has no attribute '{name}'"
        raise AttributeError(msg)


class NixConfig(BaseModel):
    model_config = {"populate_by_name": True}
    secrets_path: str = Field(alias="secretsPath")
    secrets_nix_path: str | None = Field(alias="secretsNixPath", default=None)
    identities: list[str]
    keys: KeyGroups
    secrets: list[SecretDef]
    agenix_bin: str | None = Field(alias="agenixBin", default=None)

    @model_validator(mode="after")
    def _validate_secret_keys_nonempty(self) -> "NixConfig":
        for s in self.secrets:
            if not s.keys:
                raise ValueError(
                    f"Secret '{s.name}' has an empty key list — "
                    f"the referenced key group has no members"
                )
        return self


CACHE_PATHS = [
    Path("/etc/agenix/agenix-manager-cache.json"),
]


def _user_cache_path(host: str) -> Path:
    return Path.home() / ".cache" / "agenix-manager" / f"{host}.json"


def load_from_cache(host: str | None = None) -> NixConfig | None:
    hostname = host or socket.gethostname()
    cache_paths = CACHE_PATHS + [_user_cache_path(hostname)]
    for path in cache_paths:
        if path.exists():
            try:
                return NixConfig.model_validate(json.loads(path.read_text()))
            except (json.JSONDecodeError, OSError):
                continue
    return None


def load_from_nix_eval(host: str | None = None, flake_ref: str = ".") -> NixConfig:
    hostname = host or socket.gethostname()
    attr = f"{flake_ref}#nixosConfigurations.{hostname}.config.agenixManager.cliConfig"
    try:
        result = subprocess.run(
            ["nix", "eval", attr, "--json", "--impure"],
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        raise AgenixOpError(
            command="nix eval",
            stderr=e.stderr or f"Failed to evaluate {attr}",
            returncode=e.returncode,
        ) from e
    return NixConfig.model_validate(json.loads(result.stdout))


def load_from_file(path: Path) -> NixConfig:
    return NixConfig.model_validate(json.loads(path.read_text()))
