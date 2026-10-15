"""Remembered user preferences: window geometry and the last used folder.

Stored values come from earlier runs (or older versions), so every value is
validated when read and anything unusable falls back to a safe default; a broken
setting must never prevent the application from starting. Only paths and window
geometry are stored – never passwords or document contents.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Protocol

from PySide6.QtCore import QByteArray, QSettings
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QWidget

logger = logging.getLogger(__name__)

# ASCII on purpose: the name becomes a registry key (Windows) or a file name (macOS).
_SETTINGS_NAME = "PDF Nastroje"
_LAST_DIRECTORY_KEY = "paths/last_directory"
_WINDOW_GEOMETRY_KEY = "window/geometry"
THEMES = (("light", "Svetlá"), ("dark", "Tmavá"), ("system", "Podľa systému"))
THUMBNAIL_SIZES = ((110, "Malé"), (150, "Stredné"), (190, "Veľké"))


class _Store(Protocol):
    def value(self, key: str, defaultValue: Any = None) -> Any: ...

    def setValue(self, key: str, value: Any) -> None: ...


class _MemoryStore:
    """Stand-in for QSettings that keeps values only for the lifetime of the object (used by tests)."""

    def __init__(self) -> None:
        self._values: dict[str, Any] = {}

    def value(self, key: str, defaultValue: Any = None) -> Any:
        return self._values.get(key, defaultValue)

    def setValue(self, key: str, value: Any) -> None:
        self._values[key] = value


class Settings:
    def __init__(self, store: _Store | None = None) -> None:
        self._store: _Store = store if store is not None else _MemoryStore()

    @classmethod
    def for_application(cls) -> Settings:
        """Settings persisted in the user's profile (registry on Windows, a plist on macOS)."""
        return cls(QSettings(QSettings.Format.NativeFormat, QSettings.Scope.UserScope, _SETTINGS_NAME, _SETTINGS_NAME))

    def last_directory(self) -> Path:
        """The folder last used to open or save a file, or the home folder if it no longer exists."""
        value = self._read(_LAST_DIRECTORY_KEY)
        if isinstance(value, str) and value:
            path = Path(value)
            # A removed folder, an unplugged drive or a disconnected network share is common.
            if path.is_dir():
                return path
        return Path.home()

    def remember_directory(self, path: Path) -> None:
        """Remember the folder of `path` (a file) or `path` itself (a folder)."""
        path = Path(path)
        folder = path if path.is_dir() else path.parent
        self._store.setValue(_LAST_DIRECTORY_KEY, str(folder))

    def theme(self) -> str:
        value = self._read("appearance/theme")
        return value if isinstance(value, str) and value in dict(THEMES) else "light"

    def thumbnail_size(self) -> int:
        value = self._read("appearance/thumbnail_size")
        try:
            size = int(value)
        except (TypeError, ValueError, OverflowError):
            return 150
        return size if size in dict(THUMBNAIL_SIZES) else 150

    def image_format(self) -> str:
        value = self._read("merge/image_format")
        return value if value in ("a4", "image") else "a4"

    def set_preferences(self, theme: str, thumbnail_size: int, image_format: str) -> None:
        if theme not in dict(THEMES) or thumbnail_size not in dict(THUMBNAIL_SIZES) or image_format not in ("a4", "image"):
            raise ValueError("invalid application preferences")
        self._store.setValue("appearance/theme", theme)
        self._store.setValue("appearance/thumbnail_size", thumbnail_size)
        self._store.setValue("merge/image_format", image_format)

    def check_for_updates(self) -> bool:
        value = self._read("updates/check")
        # QSettings returns booleans as strings from the Windows registry and some plists.
        return value not in (False, "false")

    def set_check_for_updates(self, enabled: bool) -> None:
        self._store.setValue("updates/check", bool(enabled))

    def restore_window(self, window: QWidget) -> None:
        """Restore the size and position saved by `save_window`; keep the defaults if unusable."""
        value = self._read(_WINDOW_GEOMETRY_KEY)
        if not isinstance(value, QByteArray | bytes) or not window.restoreGeometry(QByteArray(value)):
            return
        # restoreGeometry moves windows from screens that are gone, but double-check: a window
        # restored where nobody can see it would look like the application did not start.
        if not any(
            screen.availableGeometry().intersects(window.frameGeometry()) for screen in QGuiApplication.screens()
        ):
            screen = QGuiApplication.primaryScreen()
            if screen is not None:
                window.move(screen.availableGeometry().topLeft())

    def save_window(self, window: QWidget) -> None:
        self._store.setValue(_WINDOW_GEOMETRY_KEY, window.saveGeometry())

    def _read(self, key: str) -> Any:
        try:
            return self._store.value(key)
        except Exception:  # noqa: BLE001 – a corrupt store must not stop the application
            logger.warning("Nastavenie %s sa nepodarilo načítať", key, exc_info=True)
            return None
