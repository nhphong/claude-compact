"""Installer for Claude Code compaction hooks."""

import json
import shutil
import sys
from pathlib import Path

from . import config

# Hook script names
PRECOMPACT_HOOK = "claude-compact-precompact.py"
SESSIONSTART_HOOK = "claude-compact-sessionstart.py"

# Claude Code settings file
SETTINGS_FILE = config.CLAUDE_DIR / "settings.json"


def get_hook_source_paths() -> tuple[Path, Path]:
    """Get paths to the hook source files in the package."""
    hooks_dir = Path(__file__).parent / "hooks"
    return hooks_dir / "precompact.py", hooks_dir / "sessionstart.py"


def get_hook_dest_paths() -> tuple[Path, Path]:
    """Get paths where hooks should be installed."""
    return (
        config.HOOKS_DIR / PRECOMPACT_HOOK,
        config.HOOKS_DIR / SESSIONSTART_HOOK,
    )


def install_hook_with_python_path(src: Path, dest: Path) -> None:
    """Copy hook file with shebang replaced to use absolute Python path.

    This ensures the hook runs with the same Python that has claude-compact
    and its dependencies installed.
    """
    content = src.read_text()

    # Replace generic shebang with absolute Python path
    python_path = sys.executable
    content = content.replace("#!/usr/bin/env python3", f"#!{python_path}", 1)

    dest.write_text(content)


def load_settings() -> dict:
    """Load Claude Code settings.json."""
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def save_settings(settings: dict) -> None:
    """Save Claude Code settings.json."""
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)


def get_hook_config(trigger: str = "both") -> dict:
    """Generate hook configuration for settings.json.

    Args:
        trigger: "auto", "manual", or "both" (default)
    """
    precompact_path = config.HOOKS_DIR / PRECOMPACT_HOOK
    sessionstart_path = config.HOOKS_DIR / SESSIONSTART_HOOK

    # Build PreCompact entries based on trigger
    if trigger == "both":
        precompact_entries = [
            {
                "matcher": "auto",
                "hooks": [{"type": "command", "command": str(precompact_path)}],
            },
            {
                "matcher": "manual",
                "hooks": [{"type": "command", "command": str(precompact_path)}],
            },
        ]
    else:
        precompact_entries = [
            {
                "matcher": trigger,
                "hooks": [{"type": "command", "command": str(precompact_path)}],
            }
        ]

    return {
        "PreCompact": precompact_entries,
        "SessionStart": [
            {
                "matcher": "compact",
                "hooks": [
                    {
                        "type": "command",
                        "command": str(sessionstart_path),
                    }
                ],
            }
        ],
    }


def install_hooks() -> tuple[bool, str]:
    """
    Install hooks into Claude Code.

    Returns:
        Tuple of (success, message)
    """
    try:
        # Ensure directories exist
        config.ensure_dirs()

        # Copy hook scripts with absolute Python path in shebang
        precompact_src, sessionstart_src = get_hook_source_paths()
        precompact_dest, sessionstart_dest = get_hook_dest_paths()

        install_hook_with_python_path(precompact_src, precompact_dest)
        install_hook_with_python_path(sessionstart_src, sessionstart_dest)

        # Make hooks executable
        precompact_dest.chmod(0o755)
        sessionstart_dest.chmod(0o755)

        # Load current settings
        settings = load_settings()

        # Get trigger configuration
        trigger = config.get_config_value("trigger")

        # Merge hook configuration
        hook_config = get_hook_config(trigger)

        if "hooks" not in settings:
            settings["hooks"] = {}

        # Add our hooks (preserving other hooks)
        for hook_type, hook_list in hook_config.items():
            if hook_type not in settings["hooks"]:
                settings["hooks"][hook_type] = []

            # Remove any existing claude-compact hooks
            settings["hooks"][hook_type] = [
                h for h in settings["hooks"][hook_type]
                if not any(
                    "claude-compact" in str(hook.get("command", ""))
                    for hook in h.get("hooks", [])
                )
            ]

            # Add our hooks
            settings["hooks"][hook_type].extend(hook_list)

        # Save settings
        save_settings(settings)

        # Initialize config file with defaults if it doesn't exist
        if not config.CONFIG_FILE.exists():
            config.save_config(config.DEFAULT_CONFIG.copy())

        return True, "Hooks installed successfully"

    except Exception as e:
        return False, f"Installation failed: {e}"


def uninstall_hooks() -> tuple[bool, str]:
    """
    Uninstall hooks from Claude Code and clean up all related files.

    Returns:
        Tuple of (success, message)
    """
    try:
        # Remove hook scripts
        precompact_dest, sessionstart_dest = get_hook_dest_paths()

        if precompact_dest.exists():
            precompact_dest.unlink()
        if sessionstart_dest.exists():
            sessionstart_dest.unlink()

        # Load current settings
        settings = load_settings()

        if "hooks" in settings:
            # Remove our hooks from each hook type
            for hook_type in ["PreCompact", "SessionStart"]:
                if hook_type in settings["hooks"]:
                    settings["hooks"][hook_type] = [
                        h for h in settings["hooks"][hook_type]
                        if not any(
                            "claude-compact" in str(hook.get("command", ""))
                            for hook in h.get("hooks", [])
                        )
                    ]

                    # Remove empty lists
                    if not settings["hooks"][hook_type]:
                        del settings["hooks"][hook_type]

            # Remove empty hooks object
            if not settings["hooks"]:
                del settings["hooks"]

            # Save settings
            save_settings(settings)

        # Remove config file
        if config.CONFIG_FILE.exists():
            config.CONFIG_FILE.unlink()

        # Remove exports folder
        export_dir = config.get_export_dir()
        if export_dir.exists():
            shutil.rmtree(export_dir)

        # Remove continuation prompt file if exists
        continuation_file = config.HOOKS_DIR / "continuation_prompt.txt"
        if continuation_file.exists():
            continuation_file.unlink()

        return True, "Uninstalled hooks, config, and exports"

    except Exception as e:
        return False, f"Uninstallation failed: {e}"


def is_installed() -> bool:
    """Check if hooks are currently installed."""
    precompact_dest, sessionstart_dest = get_hook_dest_paths()

    if not precompact_dest.exists() or not sessionstart_dest.exists():
        return False

    settings = load_settings()
    if "hooks" not in settings:
        return False

    # Check if our hooks are in settings
    has_precompact = False
    has_sessionstart = False

    for hook in settings["hooks"].get("PreCompact", []):
        for h in hook.get("hooks", []):
            if "claude-compact" in str(h.get("command", "")):
                has_precompact = True
                break

    for hook in settings["hooks"].get("SessionStart", []):
        for h in hook.get("hooks", []):
            if "claude-compact" in str(h.get("command", "")):
                has_sessionstart = True
                break

    return has_precompact and has_sessionstart


def get_status() -> dict:
    """Get detailed installation status."""
    precompact_dest, sessionstart_dest = get_hook_dest_paths()

    return {
        "installed": is_installed(),
        "precompact_hook_exists": precompact_dest.exists(),
        "sessionstart_hook_exists": sessionstart_dest.exists(),
        "settings_file": str(SETTINGS_FILE),
        "hooks_dir": str(config.HOOKS_DIR),
        "config_file": str(config.CONFIG_FILE),
        "exports_dir": str(config.get_export_dir()),
    }
