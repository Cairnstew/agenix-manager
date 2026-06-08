from __future__ import annotations

import socket
from pathlib import Path
from typing import Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import Input, Label, SelectionList, Static, TextArea

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


class NewSecretScreen(WizardScreen):
    total_steps = 5

    BINDINGS = [
        Binding("escape", "go_back_or_exit", "Back"),
        Binding("ctrl+enter", "confirm_step", "Confirm"),
    ]

    CSS = """
    .hidden { display: none; }
    .error { color: $error; }
    #wizard-container { padding: 1 2; }
    #step-title { padding-bottom: 0; }
    #step-description { padding-bottom: 1; }
    #step-hint { padding-top: 1; text-align: center; color: $text-muted; }
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
        self.secret_hosts: list[str] | None = None
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
            with Vertical(id="hosts-section", classes="hidden"):
                yield Label("[b]Host filter[/]", classes="field-label")
                yield Input(
                    placeholder="e.g. host1, host2 (leave empty for all hosts)",
                    id="hosts-input",
                )
                yield Label(
                    "Optional: comma-separated hostnames that should receive this secret. "
                    "Leave empty to register on all hosts.",
                    classes="field-hint",
                )
            yield Static("", id="step-hint")

    def on_mount(self) -> None:
        self._render_step(1)

    def _render_step(self, step: int) -> None:
        title = self.query_one("#step-title", Static)
        desc = self.query_one("#step-description", Static)
        hint = self.query_one("#step-hint", Static)
        name_section = self.query_one("#name-section", Vertical)
        scope_section = self.query_one("#scope-section", Vertical)
        perms_section = self.query_one("#perms-section", Vertical)
        secret_value_section = self.query_one("#secret-value-section", Vertical)
        hosts_section = self.query_one("#hosts-section", Vertical)

        name_section.classes = "hidden" if step != 1 else ""
        scope_section.classes = "hidden" if step != 2 else ""
        perms_section.classes = "hidden" if step != 3 else ""
        secret_value_section.classes = "hidden" if step != 4 else ""
        hosts_section.classes = "hidden" if step != 5 else ""

        if step == 1:
            title.update("[bold]Step 1/5: Secret name[/]")
            desc.update(
                "Enter a name for the new secret (alphanumeric, hyphens, underscores only)"
            )
            hint.update("[dim][Enter][/dim] to continue  [dim][Esc][/dim] to exit")
            self.query_one("#name-input", Input).focus()
        elif step == 2:
            title.update("[bold]Step 2/5: Key scope[/]")
            desc.update(
                "Select which key group should be able to decrypt this secret"
            )
            hint.update(
                "[dim][Space][/dim] to select  [dim][Ctrl+Enter][/dim] to continue  [dim][Esc][/dim] to go back"
            )
            if not self._scope_list_populated:
                self._scope_list_populated = True
                selection_list = self.query_one("#scope-list", SelectionList)
                extra = (
                    self.cfg.keys.model_extra
                    if hasattr(self.cfg.keys, "model_extra")
                    else {}
                )
                groups = (
                    {k: len(v) for k, v in extra.items()}
                    if extra
                    else {}
                )
                options = []
                for scope_name, count in groups.items():
                    label = f"{scope_name}  ({count} key{'s' if count != 1 else ''})"
                    options.append(
                        (label, scope_name, scope_name == self.secret_scope)
                    )
                selection_list.add_options(options)
            self.query_one("#scope-list", SelectionList).focus()
        elif step == 3:
            title.update("[bold]Step 3/5: Permissions[/]")
            desc.update("Set file owner, group, and mode for the decrypted secret")
            hint.update(
                "[dim][Tab][/dim] between fields  [dim][Enter][/dim] to continue  [dim][Esc][/dim] to go back"
            )
            self.query_one("#owner-input", Input).focus()
        elif step == 4:
            title.update("[bold]Step 4/5: Secret value[/]")
            desc.update("Enter the secret value (paste or type the content)")
            hint.update(
                "[dim][Enter][/dim] to continue  [dim][Esc][/dim] to go back"
            )
            self.query_one("#secret-value-input", TextArea).focus()
        elif step == 5:
            title.update("[bold]Step 5/5: Host filter[/]")
            desc.update(
                "Restrict this secret to specific hosts (optional)"
            )
            hint.update(
                "[dim][Enter][/dim] to create  [dim][Esc][/dim] to go back"
            )
            self.query_one("#hosts-input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "name-input" and self.step == 1:
            if self._validate_step(1):
                self.step = 2
                self._render_step(2)
        elif event.input.id in ("owner-input", "group-input", "mode-input") and self.step == 3:
            if self._validate_step(3):
                self.step = 4
                self._render_step(4)
        elif event.input.id == "secret-value-input" and self.step == 4:
            if self._validate_step(4):
                self.step = 5
                self._render_step(5)

    def action_confirm_step(self) -> None:
        if self.step == 2:
            if self._validate_step(2):
                self.step = 3
                self._render_step(3)
        elif self.step == 5:
            self.run_worker(self._on_finish())
        else:
            self.notify(
                "Press Enter on the input field to continue",
                severity="information",
            )

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

    async def _on_finish(self) -> None:
        owner_input = self.query_one("#owner-input", Input)
        group_input = self.query_one("#group-input", Input)
        mode_input = self.query_one("#mode-input", Input)
        secret_input = self.query_one("#secret-value-input", TextArea)
        hosts_input = self.query_one("#hosts-input", Input)

        owner = owner_input.value.strip() or "root"
        group = group_input.value.strip() or "root"
        mode = mode_input.value.strip() or "0400"
        plaintext = secret_input.text

        raw_hosts = hosts_input.value.strip()
        hosts_list: list[str] | None = None
        if raw_hosts:
            hosts_list = [h.strip() for h in raw_hosts.split(",") if h.strip()]

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
        self.secret_hosts = hosts_list

        try:
            self.manifest = add_secret(
                self.manifest,
                name=self.secret_name,
                scope=self.secret_scope,
                hosts=self.secret_hosts,
                owner=self.secret_owner,
                group=self.secret_group,
                mode=self.secret_mode,
            )
            save_manifest(self.manifest_path, self.manifest)

            resolved = resolve_all(
                self.manifest, self.cfg.keys, self.cfg.secrets_path, socket.gethostname()
            )
            updated_cfg = self.cfg.model_copy(update={"secrets": resolved})
            self.app.cfg = updated_cfg
            write_secrets_nix(updated_cfg)

            secret = next(s for s in resolved if s.name == self.secret_name)

            encrypt_secret_from_stdin(updated_cfg, secret, plaintext)

            self.notify(
                f"[bold green]Secret '{self.secret_name}' created![/]",
                severity="information",
                timeout=10,
            )
            self.dismiss(True)
        except ManifestError as e:
            self.notify(f"Manifest error: {e}", severity="error")
        except AgenixOpError as e:
            self.notify(f"Encryption failed: {e.stderr}", severity="error")
