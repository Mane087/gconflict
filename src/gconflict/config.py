"""Load gconflict user configuration."""

from dataclasses import dataclass
from pathlib import Path
import tomllib


CONFIG_PATH = Path.home() / ".config" / "gconflict" / "config.toml"


class ConfigError(ValueError):
    """Report invalid user configuration."""


@dataclass(frozen=True)
class AppConfig:
    """Store supported user configuration."""

    editor: str | None = None
    collapsible_actions: bool = True
    show_status_line: bool = True
    show_command_palette: bool = True
    theme: str | None = None


def load_config(path: Path | None = None) -> AppConfig:
    """Load the fixed user configuration path or return defaults."""
    config_path = CONFIG_PATH if path is None else path
    if not config_path.exists():
        return AppConfig()

    try:
        values = tomllib.loads(config_path.read_text())
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as error:
        raise ConfigError(f"cannot read {config_path}: {error}") from error

    _validate_optional_string(values, "editor")
    _validate_boolean(values, "collapsible_actions")
    _validate_boolean(values, "show_status_line")
    _validate_boolean(values, "show_command_palette")
    _validate_optional_string(values, "theme")

    return AppConfig(
        editor=values.get("editor"),
        collapsible_actions=values.get("collapsible_actions", True),
        show_status_line=values.get("show_status_line", True),
        show_command_palette=values.get("show_command_palette", True),
        theme=values.get("theme"),
    )


def _validate_optional_string(values: dict[str, object], key: str) -> None:
    """Require a supported optional string value."""
    value = values.get(key)
    if value is not None and not isinstance(value, str):
        raise ConfigError(f"{key} must be a string.")


def _validate_boolean(values: dict[str, object], key: str) -> None:
    """Require a supported boolean value."""
    if key in values and not isinstance(values[key], bool):
        raise ConfigError(f"{key} must be a boolean.")
