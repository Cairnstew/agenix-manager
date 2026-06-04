"""Import every screen module so that each one self-registers
with ScreenRegistry before the app starts."""

from . import (
    decrypt,
    decrypt_view,
    encrypt,
    main_menu,
    new_secret,
    rekey,
    rekey_confirm,
    remove,
    status,
)
from .decrypt import DecryptScreen
from .decrypt_view import DecryptViewScreen
from .encrypt import EncryptScreen
from .main_menu import MainMenuScreen
from .new_secret import NewSecretScreen
from .rekey import RekeyScreen
from .rekey_confirm import RekeyConfirmScreen
from .remove import RemoveScreen
from .status import StatusScreen

__all__ = [
    "DecryptScreen",
    "DecryptViewScreen",
    "EncryptScreen",
    "MainMenuScreen",
    "NewSecretScreen",
    "RekeyConfirmScreen",
    "RekeyScreen",
    "RemoveScreen",
    "StatusScreen",
]
