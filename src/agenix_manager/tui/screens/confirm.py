from __future__ import annotations

from typing import Any

from textual.app import ComposeResult
from textual.widgets import Label, Static

from ..base import ConfirmModalScreen


class GenericConfirmScreen(ConfirmModalScreen):
    """Generic yes/no confirmation modal.

    Reusable by any operation that needs a simple confirmation
    before proceeding. Renders a title and message body with
    consistent styling.
    """

    def __init__(self, title: str, message: str, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._confirm_title = title
        self._confirm_message = message

    def compose(self) -> ComposeResult:
        yield Label(self._confirm_title, id="confirm-title")
        yield Static(self._confirm_message, id="confirm-message")
        yield Label(
            "[dim]y[/] confirm  [dim]n[/] / [dim]esc[/] cancel",
            id="confirm-hint",
        )

    def on_mount(self) -> None:
        title = self.query_one("#confirm-title", Label)
        title.styles.padding = (1, 2)
        msg = self.query_one("#confirm-message", Static)
        msg.styles.padding = (1, 2)
        msg.styles.border = ("solid", "grey")
        msg.styles.max_height = "80%"
        hint = self.query_one("#confirm-hint", Label)
        hint.styles.padding = (1, 2)
        hint.styles.text_align = "center"
