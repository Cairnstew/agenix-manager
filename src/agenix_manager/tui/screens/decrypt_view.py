from __future__ import annotations

from textual.app import ComposeResult
from textual.widgets import Static

from ..base import ViewerModalScreen


class DecryptViewScreen(ViewerModalScreen):
    def __init__(self, plaintext: str, secret_name: str) -> None:
        super().__init__()
        self.plaintext = plaintext
        self.secret_name = secret_name

    def compose(self) -> ComposeResult:
        yield Static(
            "[bold red]⚠ EPHEMERAL — content not saved to disk[/]",
            id="ephemeral-banner",
        )
        yield Static(self.plaintext, id="plaintext-content")

    def on_mount(self) -> None:
        banner = self.query_one("#ephemeral-banner", Static)
        banner.styles.background = "red"
        banner.styles.color = "white"
        banner.styles.text_align = "center"
        banner.styles.padding = (1, 2)
        content = self.query_one("#plaintext-content", Static)
        content.styles.padding = (1, 2)
        content.styles.border = ("solid", "grey")

    def on_unmount(self) -> None:
        self.plaintext = ""
