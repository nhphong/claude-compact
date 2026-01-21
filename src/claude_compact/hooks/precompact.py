#!/usr/bin/env python3
"""
PreCompact hook: Exports the full conversation before compaction.

This script is called by Claude Code before compaction occurs.
It uses claude-extract to export the current session to a markdown file.
"""

import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Config paths (must match config.py)
HOOKS_DIR = Path.home() / ".claude/hooks"
CONFIG_FILE = HOOKS_DIR / "claude-compact-config.json"
CONTINUATION_FILE = HOOKS_DIR / "continuation_prompt.txt"
LOG_FILE = HOOKS_DIR / "claude-compact.log"


def log_error(message: str) -> None:
    """Append error message to log file for debugging."""
    try:
        timestamp = datetime.now().isoformat()
        with open(LOG_FILE, "a") as f:
            f.write(f"[{timestamp}] [precompact] {message}\n")
    except IOError:
        pass

# Defaults
DEFAULT_EXPORT_DIR = HOOKS_DIR / "exports"
DEFAULT_FORMAT = "markdown"
DEFAULT_DETAILED = True
DEFAULT_CLEANUP_ENABLED = True
DEFAULT_CLEANUP_MODE = "age"
DEFAULT_CLEANUP_MAX_AGE_DAYS = 30
DEFAULT_CLEANUP_MAX_COUNT = 50


def load_config() -> dict:
    """Load configuration."""
    config = {
        "export_dir": str(DEFAULT_EXPORT_DIR),
        "export_format": DEFAULT_FORMAT,
        "detailed": DEFAULT_DETAILED,
        "cleanup_enabled": DEFAULT_CLEANUP_ENABLED,
        "cleanup_mode": DEFAULT_CLEANUP_MODE,
        "cleanup_max_age_days": DEFAULT_CLEANUP_MAX_AGE_DAYS,
        "cleanup_max_count": DEFAULT_CLEANUP_MAX_COUNT,
    }

    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE) as f:
                saved = json.load(f)
            config.update(saved)
        except (json.JSONDecodeError, IOError):
            pass

    return config


def cleanup_exports(config: dict, export_dir: Path) -> None:
    """Clean up old exports based on configuration."""
    if not config.get("cleanup_enabled", True):
        return

    if not export_dir.exists():
        return

    export_format = config.get("export_format", "markdown")
    pattern = "*.md" if export_format == "markdown" else f"*.{export_format}"
    exports = sorted(export_dir.glob(pattern), key=lambda f: f.stat().st_mtime, reverse=True)

    if not exports:
        return

    mode = config.get("cleanup_mode", "age")

    if mode == "age":
        max_age_days = config.get("cleanup_max_age_days", 30)
        cutoff = datetime.now() - timedelta(days=max_age_days)

        for export_file in exports:
            mtime = datetime.fromtimestamp(export_file.stat().st_mtime)
            if mtime < cutoff:
                try:
                    export_file.unlink()
                except IOError:
                    pass

    elif mode == "count":
        max_count = config.get("cleanup_max_count", 50)
        for export_file in exports[max_count:]:
            try:
                export_file.unlink()
            except IOError:
                pass


def main() -> None:
    """Main hook entry point."""
    try:
        # Read hook input from stdin
        hook_input = json.load(sys.stdin)
        session_id = hook_input.get("session_id", "unknown")

        # Load configuration
        config = load_config()
        export_dir = Path(config["export_dir"]).expanduser()
        export_format = config.get("export_format", "markdown")
        detailed = config.get("detailed", True)

        # Ensure export directory exists
        export_dir.mkdir(parents=True, exist_ok=True)

        # Run cleanup before export
        cleanup_exports(config, export_dir)

        # Build claude-extract command
        cmd = [
            "claude-extract",
            "--extract", "1",
            "--format", export_format,
            "--output", str(export_dir),
        ]

        if detailed:
            cmd.append("--detailed")

        # Run claude-extract
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        if result.returncode != 0:
            error_msg = f"claude-extract failed: {result.stderr}"
            print(error_msg, file=sys.stderr)
            log_error(error_msg)
            return

        # Find the most recent export file
        pattern = "*.md" if export_format == "markdown" else f"*.{export_format}"
        export_files = sorted(
            export_dir.glob(pattern),
            key=lambda f: f.stat().st_mtime,
            reverse=True
        )

        if not export_files:
            error_msg = "No export file created"
            print(error_msg, file=sys.stderr)
            log_error(error_msg)
            return

        export_path = export_files[0]

        # Save export path, session_id, and timestamp for sessionstart hook
        continuation_data = json.dumps({
            "export_path": str(export_path),
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
        })
        CONTINUATION_FILE.write_text(continuation_data)

        print(f"Exported to {export_path}", file=sys.stderr)

    except subprocess.TimeoutExpired:
        error_msg = "claude-extract timed out"
        print(error_msg, file=sys.stderr)
        log_error(error_msg)
    except FileNotFoundError:
        error_msg = "claude-extract not found. Install with: pip install claude-conversation-extractor"
        print(error_msg, file=sys.stderr)
        log_error(error_msg)
    except Exception as e:
        error_msg = f"PreCompact hook error: {e}"
        print(error_msg, file=sys.stderr)
        log_error(error_msg)


if __name__ == "__main__":
    main()
