"""Settings file, log file and bundled-resource paths for Afterburner Profile Backup."""
from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass
from datetime import datetime

_FOLDER_NAME = "AfterburnerProfileBackup"
_MAX_LOG_BYTES = 1_000_000
_HELP_FALLBACK = "The help file is missing. Please see README.md on the project page."


@dataclass
class Settings:
    install_dir: str | None = None
    install_confirmed: bool = False
    backup_root: str | None = None
    include_main_cfg: bool = True


def settings_dir() -> str:
    """Folder for settings and log. Creates it if missing. Honors ABPB_SETTINGS_DIR."""
    folder = os.environ.get("ABPB_SETTINGS_DIR")
    if not folder:
        base = os.environ.get("LOCALAPPDATA")
        if not base:
            base = os.path.join(os.path.expanduser("~"), "AppData", "Local")
        folder = os.path.join(base, _FOLDER_NAME)
    try:
        os.makedirs(folder, exist_ok=True)
    except OSError:
        pass
    return folder


def _settings_file() -> str:
    return os.path.join(settings_dir(), "settings.json")


def log_path() -> str:
    return os.path.join(settings_dir(), "log.txt")


def load_settings() -> Settings:
    """Never raises. Missing or broken file -> Settings() defaults."""
    result = Settings()
    try:
        with open(_settings_file(), "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return result
    except (OSError, ValueError) as exc:
        log("WARN", f"Could not read settings, using defaults: {type(exc).__name__}")
        return result
    if not isinstance(data, dict):
        log("WARN", "Settings file has the wrong format, using defaults.")
        return result
    for key in ("install_dir", "backup_root"):
        value = data.get(key)
        if value is None or (isinstance(value, str) and value):
            setattr(result, key, value)
    for key in ("install_confirmed", "include_main_cfg"):
        value = data.get(key)
        if isinstance(value, bool):
            setattr(result, key, value)
    return result


def save_settings(s: Settings) -> bool:
    """Writes settings.json atomically (write .tmp then os.replace). True on success."""
    path = _settings_file()
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(asdict(s), f, indent=2)
        os.replace(tmp, path)
        return True
    except (OSError, TypeError, ValueError) as exc:
        log("ERROR", f"Could not save settings: {type(exc).__name__}")
        return False


def log(level: str, message: str) -> None:
    """level is "INFO", "WARN" or "ERROR". Never raises. Rotates at 1,000,000 bytes."""
    try:
        path = log_path()
        try:
            too_big = os.path.getsize(path) > _MAX_LOG_BYTES
        except OSError:
            too_big = False
        if too_big:
            os.replace(path, os.path.join(os.path.dirname(path), "log.old.txt"))
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        text = " ".join(str(message).splitlines())
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"{stamp} {level} {text}\n")
    except Exception:
        pass


def resource_path(rel: str) -> str:
    """Path to a bundled file (sys._MEIPASS when frozen, else the repo root)."""
    base = getattr(sys, "_MEIPASS", None) if getattr(sys, "frozen", False) else None
    if not base:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *rel.split("/"))


def read_help_text() -> str:
    """Contents of docs/QUICKSTART.md, or a short friendly fallback text if missing."""
    try:
        with open(resource_path("docs/QUICKSTART.md"), "r", encoding="utf-8") as f:
            return f.read()
    except (OSError, UnicodeError):
        return _HELP_FALLBACK
