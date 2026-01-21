"""Configuration management for claude-compact."""

import json
from pathlib import Path
from typing import Any

# Default paths
CLAUDE_DIR = Path.home() / ".claude"
HOOKS_DIR = CLAUDE_DIR / "hooks"
CONFIG_FILE = HOOKS_DIR / "claude-compact-config.json"
EXPORTS_DIR = HOOKS_DIR / "exports"
CONTINUATION_FILE = HOOKS_DIR / "continuation_prompt.txt"

# Default prompt template
DEFAULT_PROMPT_TEMPLATE = """IMPORTANT: This conversation was compacted. The FULL conversation before compaction is saved at:
{export_path}

If you need details from earlier in the conversation (file paths, error messages, code changes, tool calls, decisions made, etc.), use the Read tool to read that file."""

# Default configuration
DEFAULT_CONFIG = {
    "export_dir": str(EXPORTS_DIR),
    "export_format": "markdown",
    "detailed": True,
    "trigger": "*",
    "cleanup_enabled": True,
    "cleanup_mode": "age",
    "cleanup_max_age_days": 30,
    "cleanup_max_count": 50,
    "prompt_template": DEFAULT_PROMPT_TEMPLATE,
}


def ensure_dirs() -> None:
    """Ensure required directories exist."""
    HOOKS_DIR.mkdir(parents=True, exist_ok=True)
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> dict[str, Any]:
    """Load configuration from file, using defaults for missing values."""
    ensure_dirs()

    config = DEFAULT_CONFIG.copy()

    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE) as f:
                saved_config = json.load(f)
            config.update(saved_config)
        except (json.JSONDecodeError, IOError):
            pass

    return config


def save_config(config: dict[str, Any]) -> None:
    """Save configuration to file."""
    ensure_dirs()

    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def get_config_value(key: str) -> Any:
    """Get a single configuration value."""
    config = load_config()
    return config.get(key, DEFAULT_CONFIG.get(key))


def set_config_value(key: str, value: Any) -> None:
    """Set a single configuration value."""
    config = load_config()

    # Type conversion based on default config type
    if key in DEFAULT_CONFIG:
        default_type = type(DEFAULT_CONFIG[key])
        if default_type == bool:
            value = str(value).lower() in ("true", "1", "yes", "on")
        elif default_type == int:
            value = int(value)

    config[key] = value
    save_config(config)


def reset_config() -> None:
    """Reset configuration to defaults."""
    save_config(DEFAULT_CONFIG.copy())


def get_export_dir() -> Path:
    """Get the exports directory path."""
    return Path(get_config_value("export_dir")).expanduser()


def get_prompt_template() -> str:
    """Get the continuation prompt template."""
    return get_config_value("prompt_template")


def set_prompt_template(template: str) -> None:
    """Set a custom continuation prompt template."""
    set_config_value("prompt_template", template)


def reset_prompt_template() -> None:
    """Reset prompt template to default."""
    set_config_value("prompt_template", DEFAULT_PROMPT_TEMPLATE)
