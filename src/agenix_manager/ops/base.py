from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from ..config import NixConfig
from .errors import AgenixOpError

_AGENIX_CANDIDATES = [
    "/run/current-system/sw/bin/agenix",
    "/nix/var/nix/profiles/default/bin/agenix",
    "/nix/var/nix/profiles/system/sw/bin/agenix",
    "/run/wrappers/bin/agenix",
]

_AGE_CANDIDATES = [
    "/run/current-system/sw/bin/age",
    "/nix/var/nix/profiles/default/bin/age",
    "/nix/var/nix/profiles/system/sw/bin/age",
    "/run/wrappers/bin/age",
]


class BaseOp:
    """Shared infrastructure for all secret operations.

    Provides binary discovery, subprocess invocation with consistent
    error wrapping, and the RULES path helper used by agenix.
    """

    def __init__(self, cfg: NixConfig) -> None:
        self.cfg = cfg

    # ── binary discovery ──────────────────────────────────────────────

    def _find_agenix(self) -> str:
        # 1. AGENIX_BIN env var (set by home-manager module or manually).
        env_bin = os.environ.get("AGENIX_BIN")
        if env_bin:
            return env_bin

        # 2. Config value (written by NixOS module cliConfig cache).
        if self.cfg.agenix_bin:
            return self.cfg.agenix_bin

        # 3. PATH lookup.
        found = shutil.which("agenix")
        if found:
            return found

        # 4. Well-known NixOS / Nix profile paths.
        candidates = list(_AGENIX_CANDIDATES)
        sudo_user = os.environ.get("SUDO_USER")
        if sudo_user:
            candidates.insert(0, f"/home/{sudo_user}/.nix-profile/bin/agenix")
            candidates.insert(0, f"/etc/profiles/per-user/{sudo_user}/bin/agenix")
        for candidate in candidates:
            if Path(candidate).exists():
                return candidate

        raise AgenixOpError(
            command="agenix --help",
            stderr=(
                "agenix binary not found.\n"
                "Install it via your NixOS configuration:\n"
                "  1. Add agenix to your flake inputs.\n"
                "  2. Set agenixManager.agenixPackage = agenix.packages.${pkgs.system}.default;\n"
                "     (this is automatic when using the flake's nixosModules.default).\n"
                "Or set the AGENIX_BIN environment variable to the agenix binary path."
            ),
            returncode=1,
        )

    def _find_age(self) -> str:
        candidates = list(_AGE_CANDIDATES)
        sudo_user = os.environ.get("SUDO_USER")
        if sudo_user:
            candidates.insert(0, f"/home/{sudo_user}/.nix-profile/bin/age")
            candidates.insert(0, f"/etc/profiles/per-user/{sudo_user}/bin/age")

        found = shutil.which("age")
        if found:
            return found

        for candidate in candidates:
            if Path(candidate).exists():
                return candidate

        raise AgenixOpError(
            command="age --help",
            stderr=(
                "age binary not found.\n"
                "Install it by adding to your NixOS configuration:\n"
                "  environment.systemPackages = [ pkgs.age ];\n"
            ),
            returncode=1,
        )

    # ── subprocess helper ─────────────────────────────────────────────

    def _run(
        self, cmd: list[str], capture: bool = True, **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        """Run *cmd* and wrap any failure in ``AgenixOpError``.

        When *capture* is ``True`` (default), ``text=True`` is set so that
        stdout/stderr pipes use string mode.  When *capture* is ``False``
        the subprocess inherits the parent's terminal (stdin/stdout/stderr
        are passed through) — use this for interactive commands like
        ``agenix -e`` that need the TTY.
        """
        if capture:
            kwargs.setdefault("text", True)
        try:
            result = subprocess.run(cmd, check=True, **kwargs)  # type: ignore[arg-type]
            return result  # type: ignore[return-value]
        except FileNotFoundError as e:
            raise AgenixOpError(
                command=" ".join(cmd),
                stderr=f"Binary not found: {e.filename}",
                returncode=255,
            ) from e
        except subprocess.CalledProcessError as e:
            stderr = ""
            if e.stderr is not None:
                stderr = e.stderr if isinstance(e.stderr, str) else e.stderr.decode("utf-8", errors="replace")
            raise AgenixOpError(
                command=" ".join(e.cmd),
                stderr=stderr,
                returncode=e.returncode,
            ) from e

    # ── RULES path for agenix ─────────────────────────────────────────

    @property
    def _rules_path(self) -> str:
        if self.cfg.secrets_nix_path:
            return self.cfg.secrets_nix_path
        return str(Path(self.cfg.secrets_path) / "secrets.nix")

    # ── RULES environment ─────────────────────────────────────────────

    @property
    def _rules_env(self) -> dict[str, str]:
        return {**os.environ, "RULES": self._rules_path}
