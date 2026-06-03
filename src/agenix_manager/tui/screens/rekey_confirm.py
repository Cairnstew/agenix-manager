from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.widgets import Label, Static

from ...config import NixConfig, SecretDef

KEYS_SNAPSHOT_PATH = Path("/etc/agenix/keys-snapshot.json")


def _load_current_keys(secret_name: str) -> list[str] | None:
    if not KEYS_SNAPSHOT_PATH.exists():
        return None
    try:
        data = json.loads(KEYS_SNAPSHOT_PATH.read_text())
        keys = data.get(secret_name)
        if keys is not None:
            return keys  # type: ignore[no-any-return]
    except (json.JSONDecodeError, OSError):
        pass
    return None


def _render_diff(current: list[str], new: list[str]) -> str:
    current_set = set(current)
    new_set = set(new)
    added = new_set - current_set
    removed = current_set - new_set

    lines = []
    if not current:
        lines.append("[yellow]New secret — no previous recipients[/]")
        lines.append("")
    elif current == new:
        lines.append("[bold]No key changes — rekey will re-encrypt to the same recipients[/]")
        lines.append("")

    if current:
        lines.append("[underline]Current recipients:[/]")
        for k in current:
            if k in removed:
                lines.append(f"  [red]- {k}[/]")
            else:
                lines.append(f"  [white]  {k}[/]")
        lines.append("")

    lines.append("[underline]New recipients:[/]")
    for k in new:
        if k in added:
            lines.append(f"  [green]+ {k}[/]")
        else:
            lines.append(f"  [white]  {k}[/]")

    if added or removed:
        count_added = len(added)
        count_removed = len(removed)
        summary = f"[bold]{count_added} added, {count_removed} removed[/]"
        lines.append("")
        lines.append(summary)

    return "\n".join(lines)


class RekeyConfirmScreen(ModalScreen[bool]):
    BINDINGS = [
        Binding("y", "confirm", "Confirm"),
        Binding("n", "cancel", "Cancel"),
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(self, cfg: NixConfig, secret: SecretDef, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.cfg = cfg
        self.secret = secret
        self.current_keys = _load_current_keys(secret.name)

    def compose(self) -> ComposeResult:
        yield Label("[bold]Rekey confirmation[/]", id="rekey-title")
        yield Static(self._diff_content(), id="rekey-diff")
        yield Label("[dim]y[/] confirm  [dim]n[/] / [dim]esc[/] cancel", id="rekey-hint")

    def _diff_content(self) -> str:
        if self.current_keys is not None:
            current = self.current_keys
        else:
            current = []
        new = self.secret.keys
        return _render_diff(current, new)

    def action_confirm(self) -> None:
        self.dismiss(True)

    def action_cancel(self) -> None:
        self.dismiss(False)

    def on_mount(self) -> None:
        self.query_one("#rekey-title", Label).styles.padding = (1, 2)
        diff = self.query_one("#rekey-diff", Static)
        diff.styles.padding = (1, 2)
        diff.styles.border = ("solid", "grey")
        diff.styles.max_height = "80%"
        hint = self.query_one("#rekey-hint", Label)
        hint.styles.padding = (1, 2)
        hint.styles.text_align = "center"
