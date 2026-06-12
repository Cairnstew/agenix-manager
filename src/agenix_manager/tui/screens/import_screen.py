from __future__ import annotations

from pathlib import Path
from typing import Any

from textual import events
from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.widgets import Label, SelectionList
from textual.widgets.selection_list import Selection


class ImportSelectScreen(ModalScreen[list[Path] | None]):
    """Shows untracked .age files with checkboxes for selective import.

    Dismisses with:
      - ``list[Path]`` — user confirmed with at least one file selected
      - ``None`` — user cancelled
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(self, untracked: list[Path], **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.untracked = untracked

    def compose(self) -> ComposeResult:
        yield Label("[bold]Select untracked secrets to import:[/]", id="import-title")
        yield SelectionList(
            *[Selection(f.name, i, True) for i, f in enumerate(self.untracked)],
            id="import-selection-list",
        )
        yield Label(
            "[dim]space[/] toggle    "
            "[dim]enter[/] import selected    "
            "[dim]esc[/] cancel",
            id="import-hint",
        )

    def on_mount(self) -> None:
        self.query_one("#import-title", Label).styles.padding = (1, 2)
        sl = self.query_one("#import-selection-list", SelectionList)
        sl.styles.margin = (0, 2)
        sl.styles.border = ("solid", "grey")
        sl.styles.max_height = "80%"
        self.query_one("#import-hint", Label).styles.padding = (1, 2)
        self.query_one("#import-hint", Label).styles.text_align = "center"
        sl.focus()

    def _do_confirm(self) -> None:
        sl = self.query_one("#import-selection-list", SelectionList)
        selected_indices = sl.selected
        if not selected_indices:
            self.notify("No files selected", severity="warning")
            return
        self.dismiss([self.untracked[i] for i in sorted(selected_indices)])

    async def _on_key(self, event: events.Key) -> None:
        if event.key == "enter":
            event.stop()
            self._do_confirm()
            return
        await super()._on_key(event)

    def action_cancel(self) -> None:
        self.dismiss(None)
