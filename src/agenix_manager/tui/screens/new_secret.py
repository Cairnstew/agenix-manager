from __future__ import annotations

from pathlib import Path
from typing import Any

from textual import events
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Label, SelectionList, Static

from ...config import NixConfig
from ...manifest import (
    Manifest,
    ManifestError,
    add_secret,
    load_manifest,
    resolve_all,
    save_manifest,
)
from ...ops.encrypt import encrypt_secret
from ...ops.errors import AgenixOpError
from ...secrets_nix import write_secrets_nix


class NewSecretScreen(Screen[None]):
    BINDINGS = [
        Binding("escape", "go_back_or_exit", "Back"),
        Binding("enter", "advance_or_create", "Confirm"),
    ]

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
    """

    def __init__(self, cfg: NixConfig, manifest_path: Path, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.cfg = cfg
        self.manifest_path = manifest_path
        self.step = 1
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

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
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
            with Horizontal(id="button-row"):
                yield Button("Cancel", id="cancel-btn", variant="default")
                yield Button("Next", id="next-btn", variant="default", classes="hidden")
                yield Button("Back", id="back-btn", variant="default", classes="hidden")
                yield Button("Create", id="create-btn", variant="success", classes="hidden")
        yield Footer()

    def on_mount(self) -> None:
        self._show_step(1)

    def _show_step(self, step: int) -> None:
        self.step = step
        title = self.query_one("#step-title", Static)
        desc = self.query_one("#step-description", Static)
        name_section = self.query_one("#name-section", Vertical)
        scope_section = self.query_one("#scope-section", Vertical)
        perms_section = self.query_one("#perms-section", Vertical)
        next_btn = self.query_one("#next-btn", Button)
        back_btn = self.query_one("#back-btn", Button)
        create_btn = self.query_one("#create-btn", Button)

        name_section.classes = "hidden" if step != 1 else ""
        scope_section.classes = "hidden" if step != 2 else ""
        perms_section.classes = "hidden" if step != 3 else ""

        if step == 1:
            title.update("[bold]Step 1/3: Secret name[/]")
            desc.update("Enter a name for the new secret (alphanumeric, hyphens, underscores only)")
            next_btn.classes = ""
            back_btn.classes = "hidden"
            create_btn.classes = "hidden"
            self.query_one("#name-input", Input).focus()
        elif step == 2:
            title.update("[bold]Step 2/3: Key scope[/]")
            desc.update("Select which key group should be able to decrypt this secret")
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
                if hasattr(self.cfg.keys, "model_extra") and self.cfg.keys.model_extra:
                    extra = {k: len(v) for k, v in self.cfg.keys.model_extra.items()}
                groups.update(extra)
                options = []
                for scope_name, count in groups.items():
                    label = f"{scope_name}  ({count} key{'s' if count != 1 else ''})"
                    options.append((label, scope_name, scope_name == self.secret_scope))
                selection_list.add_options(options)
            next_btn.classes = ""
            back_btn.classes = ""
            create_btn.classes = "hidden"
            self.query_one("#scope-list", SelectionList).focus()
        elif step == 3:
            title.update("[bold]Step 3/3: Permissions[/]")
            desc.update("Set file owner, group, and mode for the decrypted secret")
            next_btn.classes = "hidden"
            back_btn.classes = ""
            create_btn.classes = ""
            self.query_one("#owner-input", Input).focus()

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
            self.app.pop_screen()
        elif event.button.id == "next-btn":
            self._advance()
        elif event.button.id == "back-btn":
            self._go_back()
        elif event.button.id == "create-btn":
            await self._create_secret()

    async def action_advance_or_create(self) -> None:
        if self.step == 3:
            await self._create_secret()
        else:
            self._advance()

    def action_go_back_or_exit(self) -> None:
        if self.step == 1:
            self.app.pop_screen()
        else:
            self._go_back()

    def _advance(self) -> None:
        if self.step == 1:
            name_input = self.query_one("#name-input", Input)
            name = name_input.value.strip()
            error = self._validate_name(name)
            if error:
                self.query_one("#name-error", Label).update(error)
                return
            self.query_one("#name-error", Label).update("")
            self.secret_name = name
            self._show_step(2)
        elif self.step == 2:
            selection_list = self.query_one("#scope-list", SelectionList)
            selected = selection_list.selected
            if not selected:
                self.notify("Please select at least one scope", severity="warning")
                return
            if len(selected) == 1:
                self.secret_scope = selected[0]
            else:
                self.secret_scope = selected
            self._show_step(3)

    def _go_back(self) -> None:
        if self.step == 2:
            self._show_step(1)
        elif self.step == 3:
            self._show_step(2)

    async def _create_secret(self) -> None:
        owner_input = self.query_one("#owner-input", Input)
        group_input = self.query_one("#group-input", Input)
        mode_input = self.query_one("#mode-input", Input)

        owner = owner_input.value.strip() or "root"
        group = group_input.value.strip() or "root"
        mode = mode_input.value.strip() or "0400"

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

            resolved = resolve_all(self.manifest, self.cfg.keys, self.cfg.secrets_path)
            updated_cfg = self.cfg.model_copy(update={"secrets": resolved})
            write_secrets_nix(updated_cfg)

            secret = next(s for s in resolved if s.name == self.secret_name)

            with self.app.suspend():
                encrypt_secret(updated_cfg, secret)

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
