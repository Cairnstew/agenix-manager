from __future__ import annotations

from pathlib import Path
from typing import Any

from textual.app import ComposeResult
from textual.widgets import Label, Static

from ..base import ConfirmModalScreen


class ImportConfirmScreen(ConfirmModalScreen):
    """Shows a list of untracked .age files and asks y/n to import."""

    def __init__(self, untracked: list[Path], **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.untracked = untracked

    def compose(self) -> ComposeResult:
        yield Label("[bold]Import untracked secrets?[/]", id="import-title")
        yield Static(self._file_list(), id="import-files")
        yield Label(
            "[dim]y[/] import  [dim]n[/] / [dim]esc[/] cancel",
            id="import-hint",
        )

    def _file_list(self) -> str:
        lines = [f"Found {len(self.untracked)} untracked .age file(s):", ""]
        for f in self.untracked:
            lines.append(f"  [bold]{f.name}[/]")
        return "\n".join(lines)

    def on_mount(self) -> None:
        title = self.query_one("#import-title", Label)
        title.styles.padding = (1, 2)
        files = self.query_one("#import-files", Static)
        files.styles.padding = (1, 2)
        files.styles.border = ("solid", "grey")
        files.styles.max_height = "80%"
        hint = self.query_one("#import-hint", Label)
        hint.styles.padding = (1, 2)
        hint.styles.text_align = "center"
