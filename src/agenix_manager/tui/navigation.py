from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from textual.screen import Screen

from ..config import NixConfig


@dataclass
class ScreenEntry:
    """A registered screen available from the main menu.

    Attributes:
        id: Unique slug used as the ListView item id.
        label: Short display name for the menu item.
        description: One-line description shown alongside the label.
        screen_cls: The Screen subclass to instantiate.
        kwargs_factory: Optional callable that produces extra keyword
            arguments for the screen constructor (called with *cfg*).
    """

    id: str
    label: str
    description: str
    screen_cls: type[Screen[Any]]
    kwargs_factory: Callable[[NixConfig], dict[str, Any]] | None = None


class ScreenRegistry:
    """Declarative registry of all navigable screens.

    Screens self-register at module level via ``ScreenRegistry.register()``.
    The main menu iterates the registry to build its items.
    """

    _entries: list[ScreenEntry] = []

    @classmethod
    def register(cls, entry: ScreenEntry) -> None:
        cls._entries.append(entry)

    @classmethod
    def get_all(cls) -> list[ScreenEntry]:
        return list(cls._entries)

    @classmethod
    def get(cls, screen_id: str) -> ScreenEntry | None:
        for entry in cls._entries:
            if entry.id == screen_id:
                return entry
        return None

    @classmethod
    def clear(cls) -> None:
        cls._entries.clear()
