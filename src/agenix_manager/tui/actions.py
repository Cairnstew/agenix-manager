from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, TypeVar

from ..config import NixConfig, SecretDef
from ..manifest import (
    ManifestError,
    find_manifest_path,
    load_manifest,
    remove_secret,
    resolve_all,
    save_manifest,
)
from ..ops.decrypt import decrypt_secret
from ..ops.encrypt import encrypt_secret
from ..ops.errors import AgenixOpError
from ..ops.rekey import rekey_secrets
from ..secrets_nix import write_secrets_nix
from .screens.confirm import GenericConfirmScreen
from .screens.decrypt_view import DecryptViewScreen
from .screens.rekey_confirm import RekeyConfirmScreen

T = TypeVar("T")


class ActionHandler:
    def __init__(self, screen: Any) -> None:
        self.screen = screen

    @property
    def cfg(self) -> NixConfig:
        return self.screen.cfg

    def get_selected_secret(self) -> SecretDef | None:
        return self.screen._get_selected_secret()

    def refresh(self) -> None:
        self.screen._refresh_table()

    def execute(self) -> None:
        raise NotImplementedError

    def _run_guarded(self, fn: Callable[[], T], error_message: str) -> T | None:
        """Execute *fn* and wrap known failure types into a user notification.

        Catches ``OSError``, ``ManifestError``, and ``AgenixOpError``,
        notifies the user with *error_message* and the exception string,
        and returns ``None``. On success returns *fn*'s return value.
        """
        try:
            return fn()
        except (OSError, ManifestError, AgenixOpError) as e:
            self.screen._notify_err(f"{error_message}: {e}")
            return None


class NewSecretAction(ActionHandler):
    def execute(self) -> None:
        from .screens.new_secret import NewSecretScreen

        manifest_path = find_manifest_path(self.cfg.secrets_path)
        screen = NewSecretScreen(cfg=self.cfg, manifest_path=manifest_path)
        self.screen.app.push_screen(screen, self._on_complete)

    def _on_complete(self, created: bool | None) -> None:
        if created:
            self.screen.cfg = getattr(self.screen.app, "cfg", self.screen.cfg)
            self.screen._refresh_table()


class EncryptAction(ActionHandler):
    def execute(self) -> None:
        secret = self.get_selected_secret()
        if secret is None:
            return
        try:
            with self.screen.app.suspend():
                encrypt_secret(self.cfg, secret)
            self.screen._notify_ok(f"Edited existing secret '{secret.name}.age'")
        except AgenixOpError as e:
            self.screen._notify_err(f"Encrypt failed: {e.stderr}")
            return
        self.refresh()


class DecryptAction(ActionHandler):
    def execute(self) -> None:
        secret = self.get_selected_secret()
        if secret is None:
            return
        try:
            plaintext = decrypt_secret(self.cfg, secret)
        except AgenixOpError as e:
            self.screen._notify_err(f"Decrypt failed: {e.stderr}")
            return
        self.screen.app.push_screen(
            DecryptViewScreen(plaintext=plaintext, secret_name=secret.name)
        )


class RekeyAction(ActionHandler):
    def execute(self) -> None:
        secret = self.get_selected_secret()
        if secret is None:
            return
        self._pending_secret = secret
        confirm_screen = RekeyConfirmScreen(cfg=self.cfg, secret=secret)
        self.screen.app.push_screen(confirm_screen, self._on_confirmed)

    def _on_confirmed(self, confirmed: bool | None) -> None:
        if not confirmed:
            return
        secret = self._pending_secret
        try:
            rekey_secrets(self.cfg, [secret])
            self.screen._notify_ok(f"Rekeyed '{secret.name}.age'")
        except AgenixOpError as e:
            self.screen._notify_err(f"Rekey failed: {e.stderr}")
            return
        self.refresh()


class RemoveAction(ActionHandler):
    def execute(self) -> None:
        secret = self.get_selected_secret()
        if secret is None:
            return
        self._pending_secret = secret
        confirm_screen = GenericConfirmScreen(
            title="[bold red]Delete secret?[/]",
            message=(
                f"[bold]{secret.name}[/]\n"
                f"  scope : {secret.scope}\n"
                f"  file  : {secret.file}\n\n"
                "[yellow]This action cannot be undone.[/]"
            ),
        )
        self.screen.app.push_screen(confirm_screen, self._on_confirmed)

    def _on_confirmed(self, confirmed: bool | None) -> None:
        if not confirmed:
            self.screen._notify_ok("Removal cancelled")
            return
        secret = self._pending_secret
        name = secret.name

        def _do_remove() -> bool:
            age_path = Path(self.cfg.secrets_path) / f"{name}.age"
            if age_path.exists():
                age_path.unlink()
            manifest_path = find_manifest_path(self.cfg.secrets_path)
            manifest = load_manifest(manifest_path)
            manifest = remove_secret(manifest, name)
            save_manifest(manifest_path, manifest)
            resolved = resolve_all(manifest, self.cfg.keys, self.cfg.secrets_path)
            updated = self.cfg.model_copy(update={"secrets": resolved})
            self.screen.cfg = updated
            self.screen.app.cfg = updated
            write_secrets_nix(updated)
            return True

        if self._run_guarded(_do_remove, "Remove failed") is None:
            return
        self.screen._notify_ok(f"Removed secret '{name}'")
        self.refresh()
