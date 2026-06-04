from __future__ import annotations

from pathlib import Path
from typing import Any

from textual import events
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Input, Label, SelectionList, Static, TextArea

from ...config import NixConfig
from ...manifest import (
    Manifest,
    ManifestError,
    add_secret,
    find_manifest_path,
    load_manifest,
    resolve_all,
    save_manifest,
)
from ...ops.encrypt import encrypt_secret_from_stdin
from ...ops.errors import AgenixOpError
from ...secrets_nix import write_secrets_nix
from ..base import WizardScreen
from ..navigation import ScreenEntry, ScreenRegistry


class NewSecretScreen(WizardScreen):
    total_steps = 4

    CSS = """
    .hidden { display: none; }
    .error { color: $error; }
    #wizard-container { padding: 1 2; }
    #step-title { padding-bottom: 0; }
    #step-description { padding-bottom: 1; }
    #button-row { padding-top: 1; align: right middle; }
    #button-row Button { margin: 0 1; min-width: 12; text-align: center; }
    Input { margin-bottom: 0; }
    .field-label { padding-top: 1; text-style: bold; }
    .field-hint { color: $text-muted; padding-bottom: 1; }
    #scope-list { height: 10; }
    #name-error { padding-bottom: 1; }
    #secret-value-section { height: 14; }
    TextArea { height: 8; }
    """

    def __init__(self, cfg: NixConfig, manifest_path: Path, **kwargs: Any) -> None:
        super().__init__(cfg, **kwargs)
        self.manifest_path = manifest_path
        self._scope_list_populated = False

        self.secret_name = ""
        self.secret_scope: str | list[str] = "all"
        self.secret_owner = "root"
        self.secret_group = "root"
        self.secret_mode = "0400"

        try:
            self.manifest = load_manifest(manifest_path)
        except ManifestError:
            self.manifest = Manifest(version=1, secrets=[])

    def _compose_body(self) -> ComposeResult:
        with Vertical(id="wizard-container"):
            yield Static("", id="step-title")
            yield Static("", id="step-description")
            with Vertical(id="name-section"):
                yield Input(
                    placeholder="e.g. github-token",
                    id="name-input",
                )
                yield Label("", id="name-error", classes="error")
            with Vertical(id="scope-section", classes="hidden"):
                yield SelectionList(id="scope-list")
            with Vertical(id="perms-section", classes="hidden"):
                yield Label("[b]Owner[/]", classes="field-label")
                yield Input(value="root", placeholder="e.g. root", id="owner-input")
                yield Label(
                    "User that will own the decrypted secret file",
                    classes="field-hint",
                )
                yield Label("[b]Group[/]", classes="field-label")
                yield Input(value="root", placeholder="e.g. root", id="group-input")
                yield Label(
                    "Group that will own the decrypted secret file",
                    classes="field-hint",
                )
                yield Label("[b]Mode[/]", classes="field-label")
                yield Input(value="0400", placeholder="e.g. 0400", id="mode-input")
                yield Label(
                    "File permissions in octal (e.g. 0400 = read-only for owner)",
                    classes="field-hint",
                )
            with Vertical(id="secret-value-section", classes="hidden"):
                yield Label("[b]Secret value[/]", classes="field-label")
                yield TextArea(id="secret-value-input")
                yield Label(
                    "Enter the secret value. Supports multi-line content (SSH keys, configs, etc.).",
                    classes="field-hint",
                )
            with Horizontal(id="button-row"):
                yield Button("Cancel", id="cancel-btn", variant="default")
                yield Button("Next", id="next-btn", variant="primary", classes="hidden")
                yield Button("Back", id="back-btn", variant="default", classes="hidden")
                yield Button("Create", id="create-btn", variant="success", classes="hidden")

    def on_mount(self) -> None:
        self._render_step(1)

    def _render_step(self, step: int) -> None:
        title = self.query_one("#step-title", Static)
        desc = self.query_one("#step-description", Static)
        name_section = self.query_one("#name-section", Vertical)
        scope_section = self.query_one("#scope-section", Vertical)
        perms_section = self.query_one("#perms-section", Vertical)
        secret_value_section = self.query_one("#secret-value-section", Vertical)
        next_btn = self.query_one("#next-btn", Button)
        back_btn = self.query_one("#back-btn", Button)
        create_btn = self.query_one("#create-btn", Button)

        name_section.classes = "hidden" if step != 1 else ""
        scope_section.classes = "hidden" if step != 2 else ""
        perms_section.classes = "hidden" if step != 3 else ""
        secret_value_section.classes = "hidden" if step != 4 else ""

        if step == 1:
            title.update("[bold]Step 1/4: Secret name[/]")
            desc.update(
                "Enter a name for the new secret (alphanumeric, hyphens, underscores only)"
            )
            next_btn.classes = ""
            back_btn.classes = "hidden"
            create_btn.classes = "hidden"
            self.query_one("#name-input", Input).focus()
        elif step == 2:
            title.update("[bold]Step 2/4: Key scope[/]")
            desc.update(
                "Select which key group should be able to decrypt this secret"
            )
            if not self._scope_list_populated:
                self._scope_list_populated = True
                selection_list = self.query_one("#scope-list", SelectionList)
                groups = {
                    "all": (
                        len(self.cfg.keys.systems)
                        + len(self.cfg.keys.users)
                        + len(self.cfg.keys.other)
                    ),
                    "systems": len(self.cfg.keys.systems),
                    "users": len(self.cfg.keys.users),
                    "other": len(self.cfg.keys.other),
                }
                extra = {}
                if (
                    hasattr(self.cfg.keys, "model_extra")
                    and self.cfg.keys.model_extra
                ):
                    extra = {k: len(v) for k, v in self.cfg.keys.model_extra.items()}
                groups.update(extra)
                options = []
                for scope_name, count in groups.items():
                    label = f"{scope_name}  ({count} key{'s' if count != 1 else ''})"
                    options.append(
                        (label, scope_name, scope_name == self.secret_scope)
                    )
                selection_list.add_options(options)
            next_btn.classes = ""
            back_btn.classes = ""
            create_btn.classes = "hidden"
            self.query_one("#scope-list", SelectionList).focus()
        elif step == 3:
            title.update("[bold]Step 3/4: Permissions[/]")
            desc.update("Set file owner, group, and mode for the decrypted secret")
            next_btn.classes = ""
            back_btn.classes = ""
            create_btn.classes = "hidden"
            self.query_one("#owner-input", Input).focus()
        elif step == 4:
            title.update("[bold]Step 4/4: Secret value[/]")
            desc.update("Enter the secret value (paste or type the content)")
            next_btn.classes = "hidden"
            back_btn.classes = ""
            create_btn.classes = ""
            self.query_one("#secret-value-input", TextArea).focus()

    def _validate_step(self, step: int) -> bool:
        if step == 1:
            name_input = self.query_one("#name-input", Input)
            name = name_input.value.strip()
            error = self._validate_name(name)
            if error:
                self.query_one("#name-error", Label).update(error)
                return False
            self.query_one("#name-error", Label).update("")
            self.secret_name = name
            return True
        elif step == 2:
            selection_list = self.query_one("#scope-list", SelectionList)
            selected = selection_list.selected
            if not selected:
                self.notify("Please select at least one scope", severity="warning")
                return False
            if len(selected) == 1:
                self.secret_scope = selected[0]
            else:
                self.secret_scope = selected
            return True
        return True

    def _validate_name(self, name: str) -> str | None:
        import re

        if not name.strip():
            return "Name cannot be empty"
        if not re.match(r"^[a-zA-Z0-9_-]+$", name):
            return "Name must be alphanumeric with hyphens/underscores only"
        if any(s.name == name for s in self.manifest.secrets):
            return f"Secret '{name}' already exists in manifest"
        return None

    def on_key(self, event: events.Key) -> None:
        if event.key in ("left", "right"):
            focused = self.focused
            buttons = [b for b in self.query("#button-row Button") if b.display]
            if focused in buttons:
                idx = buttons.index(focused)
                if event.key == "left" and idx > 0:
                    buttons[idx - 1].focus()
                    event.stop()
                elif event.key == "right" and idx < len(buttons) - 1:
                    buttons[idx + 1].focus()
                    event.stop()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-btn":
            self.action_go_back_or_exit()
        elif event.button.id == "next-btn":
            self.action_advance_or_create()
        elif event.button.id == "back-btn":
            self.action_go_back_or_exit()
        elif event.button.id == "create-btn":
            await self._on_finish()

    async def _on_finish(self) -> None:
        owner_input = self.query_one("#owner-input", Input)
        group_input = self.query_one("#group-input", Input)
        mode_input = self.query_one("#mode-input", Input)
        secret_input = self.query_one("#secret-value-input", TextArea)

        owner = owner_input.value.strip() or "root"
        group = group_input.value.strip() or "root"
        mode = mode_input.value.strip() or "0400"
        plaintext = secret_input.text

        if not plaintext.strip():
            self.notify("Secret value cannot be empty", severity="warning")
            return

        if not mode.startswith("0") or len(mode) != 4 or not mode.isdigit():
            self.notify(
                "Mode must be a 4-digit octal string (e.g. 0400)",
                severity="error",
            )
            return

        self.secret_owner = owner
        self.secret_group = group
        self.secret_mode = mode

        try:
            self.manifest = add_secret(
                self.manifest,
                name=self.secret_name,
                scope=self.secret_scope,
                owner=self.secret_owner,
                group=self.secret_group,
                mode=self.secret_mode,
            )
            save_manifest(self.manifest_path, self.manifest)

            resolved = resolve_all(
                self.manifest, self.cfg.keys, self.cfg.secrets_path
            )
            updated_cfg = self.cfg.model_copy(update={"secrets": resolved})
            write_secrets_nix(updated_cfg)

            secret = next(s for s in resolved if s.name == self.secret_name)

            encrypt_secret_from_stdin(updated_cfg, secret, plaintext)

            self.notify(
                f"[bold green]Secret '{self.secret_name}' created![/]",
                severity="information",
                timeout=10,
            )
            self.app.pop_screen()
        except ManifestError as e:
            self.notify(f"Manifest error: {e}", severity="error")
        except AgenixOpError as e:
            self.notify(f"Encryption failed: {e.stderr}", severity="error")


ScreenRegistry.register(
    ScreenEntry(
        id="new-secret",
        label="New secret",
        description="Create a new secret",
        screen_cls=NewSecretScreen,
        kwargs_factory=lambda cfg: {"manifest_path": find_manifest_path(cfg.secrets_path)},
    )
)
