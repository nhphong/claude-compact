#!/usr/bin/env python3
"""
SessionStart hook: Injects continuation context after compaction.

This script is called by Claude Code after compaction completes.
It reads the saved export path and outputs a context message to stdout,
which Claude Code injects as context for Claude to see.
"""

import json
import sys
from datetime import datetime
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
            f.write(f"[{timestamp}] [sessionstart] {message}\n")
    except IOError:
        pass

# Default prompt template
DEFAULT_PROMPT_TEMPLATE = """IMPORTANT: This conversation was compacted. The FULL conversation before compaction is saved at:
{export_path}

If you need details from earlier in the conversation (file paths, error messages, code changes, tool calls, decisions made, etc.), use the Read tool to read that file."""


def load_config() -> dict:
    """Load configuration."""
    config = {
        "prompt_template": DEFAULT_PROMPT_TEMPLATE,
    }

    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE) as f:
                saved = json.load(f)
            config.update(saved)
        except (json.JSONDecodeError, IOError):
            pass

    return config


def main() -> None:
    """Main hook entry point."""
    # Check if continuation file exists
    if not CONTINUATION_FILE.exists():
        return

    try:
        # Read the continuation data (JSON with export_path and session_id)
        raw_data = CONTINUATION_FILE.read_text().strip()

        # Handle both old format (plain path) and new format (JSON)
        try:
            data = json.loads(raw_data)
            export_path = data.get("export_path", "")
            session_id = data.get("session_id", "")
            timestamp = data.get("timestamp", datetime.now().isoformat())
        except json.JSONDecodeError:
            # Fallback for old plain text format
            export_path = raw_data
            session_id = ""
            timestamp = datetime.now().isoformat()

        if not export_path or not Path(export_path).exists():
            error_msg = f"Export file not found: {export_path}"
            print(error_msg, file=sys.stderr)
            log_error(error_msg)
            CONTINUATION_FILE.unlink(missing_ok=True)
            return

        # Load configuration
        config = load_config()
        template = config.get("prompt_template", DEFAULT_PROMPT_TEMPLATE)

        # Format the message with available variables
        message = template.format(
            export_path=export_path,
            session_id=session_id,
            timestamp=timestamp,
        )

        # Output to stdout - Claude Code will inject this as context
        print(message)

    except Exception as e:
        error_msg = f"SessionStart hook error: {e}"
        print(error_msg, file=sys.stderr)
        log_error(error_msg)
    finally:
        # Always clean up the continuation file
        CONTINUATION_FILE.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
