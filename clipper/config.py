"""Configuration management for clipper"""

import tomllib
from pathlib import Path
from dataclasses import dataclass, field


CONFIG_DIR = Path.home() / ".config" / "clipper"
CONFIG_FILE = CONFIG_DIR / "config.toml"

DEFAULT_CONFIG = """\
# clipper configuration

[folders]
# Base folder for watch mode
# Subfolders: inbox/, processing/, done/
watch_base = "~/Movies/VidTools"

[presets]
# Default preset when none detected from filename
# Options: social, web, archive, tiny
default = "social"

[behavior]
# Auto-start watcher when TUI launches
auto_start_watcher = false

# Delete source file after successful compression (watch mode only)
delete_source = true

# Show desktop notification when job completes
notifications = true
"""


@dataclass
class FolderConfig:
    watch_base: Path = field(default_factory=lambda: Path.home() / "Movies" / "VidTools")

    @property
    def inbox(self) -> Path:
        return self.watch_base / "inbox"

    @property
    def processing(self) -> Path:
        return self.watch_base / "processing"

    @property
    def done(self) -> Path:
        return self.watch_base / "done"


@dataclass
class PresetConfig:
    default: str = "social"


@dataclass
class BehaviorConfig:
    auto_start_watcher: bool = False
    delete_source: bool = True
    notifications: bool = True


@dataclass
class Config:
    folders: FolderConfig = field(default_factory=FolderConfig)
    presets: PresetConfig = field(default_factory=PresetConfig)
    behavior: BehaviorConfig = field(default_factory=BehaviorConfig)


def ensure_config_exists() -> Path:
    """Create default config file if it doesn't exist"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not CONFIG_FILE.exists():
        CONFIG_FILE.write_text(DEFAULT_CONFIG)
    return CONFIG_FILE


def load_config() -> Config:
    """Load configuration from file"""
    ensure_config_exists()

    try:
        with open(CONFIG_FILE, "rb") as f:
            data = tomllib.load(f)
    except Exception:
        return Config()

    config = Config()

    # Folders
    if "folders" in data:
        if "watch_base" in data["folders"]:
            path = Path(data["folders"]["watch_base"]).expanduser()
            config.folders.watch_base = path

    # Presets
    if "presets" in data:
        if "default" in data["presets"]:
            config.presets.default = data["presets"]["default"]

    # Behavior
    if "behavior" in data:
        b = data["behavior"]
        if "auto_start_watcher" in b:
            config.behavior.auto_start_watcher = b["auto_start_watcher"]
        if "delete_source" in b:
            config.behavior.delete_source = b["delete_source"]
        if "notifications" in b:
            config.behavior.notifications = b["notifications"]

    return config


# Global config instance
_config: Config | None = None


def get_config() -> Config:
    """Get the global config instance"""
    global _config
    if _config is None:
        _config = load_config()
    return _config


def reload_config() -> Config:
    """Reload config from disk"""
    global _config
    _config = load_config()
    return _config


def get_config_path() -> Path:
    """Get path to config file"""
    ensure_config_exists()
    return CONFIG_FILE
