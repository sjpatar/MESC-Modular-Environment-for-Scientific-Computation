import os
import json
from pathlib import Path

class AppConfig:
    """Global configuration state for MESC."""
    _defaults = {
        "language": "en",
        "update_manifest_url": "https://github.com/Prime01-oss/MESC/releases/latest/download/release-manifest.json",
        "release_channel": "stable",
        "auto_check_updates": True,
        "skipped_version": "",
        "theme_mode": "dark",
    }
    _data = dict(_defaults)

    _config_dir = Path.home() / ".mesc"
    _config_file = _config_dir / "mesc_settings.json"

    @classmethod
    def _load(cls):
        """Silently loads the saved settings from disk on startup."""
        if cls._config_file.exists():
            try:
                with open(cls._config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        cls._data = dict(cls._defaults)
                        cls._data.update(data)
            except Exception as e:
                print(f"Failed to load config: {e}")

    @classmethod
    def _save(cls):
        """Silently saves the current state to disk."""
        try:
            cls._config_dir.mkdir(parents=True, exist_ok=True)
            with open(cls._config_file, "w", encoding="utf-8") as f:
                json.dump(cls._data, f, indent=4)
        except Exception as e:
            print(f"Failed to save config: {e}")

    @classmethod
    def get(cls, key: str, default=None):
        return cls._data.get(key, cls._defaults.get(key, default))

    @classmethod
    def set(cls, key: str, value):
        cls._data[key] = value
        cls._save()

    @classmethod
    def set_language(cls, lang: str):
        cls.set("language", lang)

    @classmethod
    def get_language(cls) -> str:
        return str(cls.get("language", "en"))

    @classmethod
    def get_update_manifest_url(cls) -> str:
        return str(cls.get("update_manifest_url", cls._defaults["update_manifest_url"]))

    @classmethod
    def set_update_manifest_url(cls, url: str):
        cls.set("update_manifest_url", url)

    @classmethod
    def get_release_channel(cls) -> str:
        return str(cls.get("release_channel", "stable"))

    @classmethod
    def set_release_channel(cls, channel: str):
        cls.set("release_channel", channel)

    @classmethod
    def get_auto_check_updates(cls) -> bool:
        return bool(cls.get("auto_check_updates", True))

    @classmethod
    def set_auto_check_updates(cls, enabled: bool):
        cls.set("auto_check_updates", bool(enabled))

    @classmethod
    def get_theme_mode(cls) -> str:
        return str(cls.get("theme_mode", "dark"))

    @classmethod
    def set_theme_mode(cls, theme_mode: str):
        cls.set("theme_mode", "light" if theme_mode == "light" else "dark")

    @classmethod
    def get_skipped_version(cls) -> str:
        return str(cls.get("skipped_version", ""))

    @classmethod
    def set_skipped_version(cls, version: str):
        cls.set("skipped_version", version or "")

AppConfig._load()
