from __future__ import annotations

from pathlib import Path
from typing import Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Label, Static


class ImportSelectScreen(ModalScreen[list[Path] | None]):
    """Shows untracked .age files with toggles for selective import.

    Dismisses with:
      - ``list[Path]`` — user confirmed with at least one file selected
      - ``None`` — user cancelled
    """

    BINDINGS = [
        Binding("space", "toggle", "Toggle"),
        Binding("enter", "confirm", "Import Selected"),
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(self, untracked: list[Path], **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.untracked = untracked
        self._selected: set[int] = set(range(len(untracked)))

    def compose(self) -> ComposeResult:
        yield Label("[bold]Select untracked secrets to import:[/]", id="import-title")
        with VerticalScroll(id="import-list-container"):
            for i, f in enumerate(self.untracked):
                checked = "x" if i in self._selected else " "
                yield Static(
                    f"[{checked}]  {f.name}",
                    id=f"import-item-{i}",
                )
        yield Label(
            "[dim]space[/] toggle    "
            "[dim]enter[/] import selected    "
            "[dim]esc[/] cancel",
            id="import-hint",
        )

    def on_mount(self) -> None:
        self.query_one("#import-title", Label).styles.padding = (1, 2)
        container = self.query_one("#import-list-container", VerticalScroll)
        container.styles.padding = (1, 2)
        container.styles.border = ("solid", "grey")
        container.styles.max_height = "80%"
        hint = self.query_one("#import-hint", Label)
        hint.styles.padding = (1, 2)
        hint.styles.text_align = "center"

    def _get_selected_files(self) -> list[Path]:
        return [self.untracked[i] for i in sorted(self._selected)]

    def action_toggle(self) -> None:
        focused = self.focused
        if focused is None or not focused.id or not focused.id.startswith("import-item-"):
            return
        idx = int(focused.id.rsplit("-", 1)[-1])
        if idx in self._selected:
            self._selected.remove(idx)
        else:
            self._selected.add(idx)
        focused.update(f"[{'x' if idx in self._selected else ' '}]  {self.untracked[idx].name}")

    def action_confirm(self) -> None:
        selected = self._get_selected_files()
        if not selected:
            self.notify("No files selected", severity="warning")
            return
        self.dismiss(selected)

    def action_cancel(self) -> None:
        self.dismiss(None)
