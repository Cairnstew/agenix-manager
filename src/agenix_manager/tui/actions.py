from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, TypeVar

from ..config import NixConfig, SecretDef
from ..manifest import (
    ManifestError,
    add_secret,
    find_manifest_path,
    load_manifest,
    remove_secret,
    resolve_all,
    save_manifest,
)
from ..ops.decrypt import decrypt_secret
from ..ops.discover import find_untracked_secrets
from ..ops.encrypt import encrypt_secret
from ..ops.errors import AgenixOpError
from ..ops.rekey import rekey_secrets
from ..secrets_nix import write_secrets_nix
from .screens.confirm import GenericConfirmScreen
from .screens.decrypt_view import DecryptViewScreen
from .screens.import_screen import ImportConfirmScreen
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
            app = self.screen.app
            driver = app._driver
            if driver is not None:
                # Manually leave alternate screen / restore terminal before
                # handing control to agenix + $EDITOR, and re-enter after.
                if hasattr(app, "_suspend_signal"):
                    app._suspend_signal()
                driver.suspend_application_mode()
                try:
                    encrypt_secret(self.cfg, secret)
                finally:
                    driver.resume_application_mode()
                    if hasattr(app, "_resume_signal"):
                        app._resume_signal()
            else:
                encrypt_secret(self.cfg, secret)
        except KeyboardInterrupt:
            self.screen._notify_warn("Encryption cancelled")
        except AgenixOpError as e:
            self.screen._notify_err(str(e))
        except Exception as e:
            self.screen._notify_err(f"Encryption failed: {e}")
        else:
            self.screen._notify_ok(f"Edited existing secret '{secret.name}.age'")
        finally:
            try:
                self.refresh()
            except Exception:
                pass


class DecryptAction(ActionHandler):
    def execute(self) -> None:
        secret = self.get_selected_secret()
        if secret is None:
            return
        try:
            plaintext = decrypt_secret(self.cfg, secret)
        except AgenixOpError as e:
            self.screen._notify_err(str(e))
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
            self.screen._notify_err(str(e))
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


class ImportAction(ActionHandler):
    def __init__(self, screen: Any, scope: str = "all") -> None:
        super().__init__(screen)
        self._scope = scope

    def execute(self) -> None:
        untracked = find_untracked_secrets(self.cfg)
        if not untracked:
            self.screen._notify_ok("No untracked .age files found")
            return
        self._pending_untracked = untracked
        confirm_screen = ImportConfirmScreen(untracked=untracked)
        self.screen.app.push_screen(confirm_screen, self._on_confirmed)

    def _on_confirmed(self, confirmed: bool | None) -> None:
        if not confirmed:
            self.screen._notify_ok("Import cancelled")
            return

        def _do_import() -> bool:
            manifest_path = find_manifest_path(self.cfg.secrets_path)
            manifest = load_manifest(manifest_path)
            for path in self._pending_untracked:
                try:
                    manifest = add_secret(
                        manifest, name=path.stem, scope=self._scope
                    )
                except ManifestError:
                    continue
            save_manifest(manifest_path, manifest)
            resolved = resolve_all(manifest, self.cfg.keys, self.cfg.secrets_path)
            updated = self.cfg.model_copy(update={"secrets": resolved})
            self.screen.cfg = updated
            self.screen.app.cfg = updated
            write_secrets_nix(updated)
            return True

        if self._run_guarded(_do_import, "Import failed") is None:
            return
        self.screen._notify_ok(
            f"Imported {len(self._pending_untracked)} secret(s)"
        )
        self.refresh()
