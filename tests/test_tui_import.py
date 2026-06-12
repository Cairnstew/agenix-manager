from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from textual.app import App
from textual.widgets import SelectionList

from agenix_manager.config import NixConfig
from agenix_manager.manifest import Manifest, find_manifest_path, load_manifest, save_manifest
from agenix_manager.tui.screens.import_screen import ImportSelectScreen


# ---------------------------------------------------------------------------
# Fixtures & helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def untracked_files(tmp_path: Path) -> list[Path]:
    secrets = tmp_path / "secrets"
    secrets.mkdir()
    for name in ("alpha", "beta", "gamma"):
        (secrets / f"{name}.age").write_text("encrypted")
    return sorted(secrets.glob("*.age"))


def _cfg(secrets_dir: str | Path) -> NixConfig:
    return NixConfig.model_validate({
        "secrets_path": str(secrets_dir),
        "identities": ["/etc/ssh/ssh_host_ed25519_key"],
        "keys": {
            "systems": ["ssh-ed25519 AAAA...systemkey"],
            "users": ["ssh-ed25519 AAAA...userkey"],
            "all": ["ssh-ed25519 AAAA...systemkey", "ssh-ed25519 AAAA...userkey"],
        },
        "secrets": [],
    })


def _prime_manifest(cfg: NixConfig) -> Path:
    manifest_path = find_manifest_path(cfg.secrets_path, cfg.manifest_path)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    save_manifest(manifest_path, Manifest(version=1, secrets=[]))
    return manifest_path


class _Harness(App[None]):

    def __init__(self, untracked: list[Path]) -> None:
        super().__init__()
        self.untracked = untracked
        self.import_result: list[Path] | None | object = ...

    def on_mount(self) -> None:
        self.push_screen(ImportSelectScreen(self.untracked), self._on_result)

    def _on_result(self, result: list[Path] | None) -> None:
        self.import_result = result


# ---------------------------------------------------------------------------
# ImportSelectScreen
# ---------------------------------------------------------------------------

class TestImportSelectScreen:

    @pytest.mark.asyncio
    async def test_shows_all_untracked(self, untracked_files: list[Path]) -> None:
        async with _Harness(untracked_files).run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            sl = pilot.app.screen.query_one("#import-selection-list", SelectionList)
            assert len(sl.selected) == 3

    @pytest.mark.asyncio
    async def test_all_selected_by_default(self, untracked_files: list[Path]) -> None:
        async with _Harness(untracked_files).run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            sl = pilot.app.screen.query_one("#import-selection-list", SelectionList)
            assert len(sl.selected) == 3

    @pytest.mark.asyncio
    async def test_enter_returns_all(self, untracked_files: list[Path]) -> None:
        async with _Harness(untracked_files).run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            sl = pilot.app.screen.query_one("#import-selection-list", SelectionList)
            assert len(sl.selected) == 3
            await pilot.press("enter")
            await pilot.pause()
            assert pilot.app.import_result == sorted(untracked_files)

    @pytest.mark.asyncio
    async def test_escape_returns_none(self, untracked_files: list[Path]) -> None:
        async with _Harness(untracked_files).run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            await pilot.press("escape")
            await pilot.pause()
            assert pilot.app.import_result is None

    @pytest.mark.asyncio
    async def test_toggle_subset(self, untracked_files: list[Path]) -> None:
        async with _Harness(untracked_files).run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            for _ in range(3):
                await pilot.press("space")
            await pilot.press("down")
            await pilot.press("down")
            await pilot.press("space")
            await pilot.press("enter")
            await pilot.pause()
            assert pilot.app.import_result == [untracked_files[1]]

    @pytest.mark.asyncio
    async def test_confirm_empty_warns(self, untracked_files: list[Path]) -> None:
        async with _Harness(untracked_files).run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            # Deselect all three items by moving down and pressing space
            for _ in range(3):
                await pilot.press("space")
                await pilot.press("down")
            await pilot.press("enter")
            await pilot.pause()
            assert pilot.app.import_result is ...
            await pilot.press("escape")
            await pilot.pause()
            assert pilot.app.import_result is None

    @pytest.mark.asyncio
    async def test_focus(self, untracked_files: list[Path]) -> None:
        async with _Harness(untracked_files).run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            sl = pilot.app.screen.query_one("#import-selection-list", SelectionList)
            assert pilot.app.focused is sl


class TestImportScreenEmpty:

    @pytest.mark.asyncio
    async def test_zero_items(self) -> None:
        async with _Harness([]).run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            sl = pilot.app.screen.query_one("#import-selection-list", SelectionList)
            assert len(sl.selected) == 0

    @pytest.mark.asyncio
    async def test_confirm_stays(self) -> None:
        async with _Harness([]).run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()
            assert pilot.app.import_result is ...

    @pytest.mark.asyncio
    async def test_cancel(self) -> None:
        async with _Harness([]).run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            await pilot.press("escape")
            await pilot.pause()
            assert pilot.app.import_result is None


# ---------------------------------------------------------------------------
# ImportAction
# ---------------------------------------------------------------------------

class TestImportAction:
    """ImportAction tests — uses lazy imports to avoid circular import
    (actions.py → screens.__init__ → status.py → actions.py)."""

    @staticmethod
    def _action(screen: MagicMock, scope: str = "all"):
        from agenix_manager.tui.actions import ImportAction
        return ImportAction(screen, scope=scope)

    @pytest.mark.asyncio
    async def test_import_all(self, untracked_files: list[Path]) -> None:
        secrets_dir = untracked_files[0].parent
        cfg = _cfg(secrets_dir)
        _prime_manifest(cfg)
        screen = MagicMock()
        screen.cfg = cfg
        self._action(screen)._on_selected(untracked_files)
        manifest = load_manifest(find_manifest_path(cfg.secrets_path, cfg.manifest_path))
        assert {s.name for s in manifest.secrets} == {"alpha", "beta", "gamma"}
        assert len(screen.cfg.secrets) == 3
        screen._notify_ok.assert_called_once()
        screen._refresh_table.assert_called_once()

    @pytest.mark.asyncio
    async def test_import_subset(self, untracked_files: list[Path]) -> None:
        secrets_dir = untracked_files[0].parent
        cfg = _cfg(secrets_dir)
        _prime_manifest(cfg)
        screen = MagicMock()
        screen.cfg = cfg
        self._action(screen)._on_selected(untracked_files[:2])
        manifest = load_manifest(find_manifest_path(cfg.secrets_path, cfg.manifest_path))
        assert {s.name for s in manifest.secrets} == {"alpha", "beta"}
        assert len(screen.cfg.secrets) == 2

    @pytest.mark.asyncio
    async def test_cancelled(self) -> None:
        screen = MagicMock()
        screen.cfg = _cfg("/tmp/nonexistent")
        self._action(screen)._on_selected(None)
        screen._notify_ok.assert_called_once_with("Import cancelled")
        screen._refresh_table.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_untracked(self) -> None:
        screen = MagicMock()
        screen.cfg = _cfg("/tmp/nonexistent")
        self._action(screen).execute()
        screen._notify_ok.assert_called_once_with("No untracked .age files found")
        screen._refresh_table.assert_not_called()

    @pytest.mark.asyncio
    async def test_duplicates(self, untracked_files: list[Path]) -> None:
        from agenix_manager.manifest import add_secret

        secrets_dir = untracked_files[0].parent
        cfg = _cfg(secrets_dir)
        manifest_path = _prime_manifest(cfg)
        manifest = load_manifest(manifest_path)
        manifest = add_secret(manifest, "alpha", scope="all")
        save_manifest(manifest_path, manifest)
        screen = MagicMock()
        screen.cfg = cfg
        self._action(screen)._on_selected(untracked_files)
        manifest = load_manifest(manifest_path)
        assert {s.name for s in manifest.secrets} == {"alpha", "beta", "gamma"}

    @pytest.mark.asyncio
    async def test_empty_selection_skips(self, untracked_files: list[Path]) -> None:
        secrets_dir = untracked_files[0].parent
        cfg = _cfg(secrets_dir)
        _prime_manifest(cfg)
        screen = MagicMock()
        screen.cfg = cfg
        self._action(screen)._on_selected([])
        screen._notify_ok.assert_called_once_with("Import cancelled")
        screen._refresh_table.assert_not_called()
