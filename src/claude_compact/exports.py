"""Export file management for claude-compact."""

import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from . import config


def get_exports() -> list[dict]:
    """
    Get list of all exported conversations.

    Returns:
        List of dicts with export info (path, size, mtime, etc.)
    """
    export_dir = config.get_export_dir()

    if not export_dir.exists():
        return []

    export_format = config.get_config_value("export_format")
    pattern = "*.md" if export_format == "markdown" else f"*.{export_format}"

    exports = []
    for f in export_dir.glob(pattern):
        stat = f.stat()
        exports.append({
            "path": f,
            "name": f.name,
            "size": stat.st_size,
            "mtime": datetime.fromtimestamp(stat.st_mtime),
            "size_human": format_size(stat.st_size),
        })

    # Sort by modification time, newest first
    exports.sort(key=lambda x: x["mtime"], reverse=True)

    return exports


def format_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def clean_exports(
    older_than_days: Optional[int] = None,
    keep_count: Optional[int] = None,
    dry_run: bool = False,
) -> list[Path]:
    """
    Clean up old exports.

    Args:
        older_than_days: Delete files older than N days
        keep_count: Keep only N most recent files
        dry_run: If True, don't actually delete, just return what would be deleted

    Returns:
        List of paths that were (or would be) deleted
    """
    exports = get_exports()

    if not exports:
        return []

    to_delete = []

    if older_than_days is not None:
        cutoff = datetime.now() - timedelta(days=older_than_days)
        for export in exports:
            if export["mtime"] < cutoff:
                to_delete.append(export["path"])

    elif keep_count is not None:
        if len(exports) > keep_count:
            for export in exports[keep_count:]:
                to_delete.append(export["path"])

    else:
        # Use configuration
        cfg = config.load_config()
        if cfg.get("cleanup_enabled", True):
            mode = cfg.get("cleanup_mode", "age")

            if mode == "age":
                max_age = cfg.get("cleanup_max_age_days", 30)
                cutoff = datetime.now() - timedelta(days=max_age)
                for export in exports:
                    if export["mtime"] < cutoff:
                        to_delete.append(export["path"])

            elif mode == "count":
                max_count = cfg.get("cleanup_max_count", 50)
                if len(exports) > max_count:
                    for export in exports[max_count:]:
                        to_delete.append(export["path"])

    if not dry_run:
        for path in to_delete:
            try:
                path.unlink()
            except IOError:
                pass

    return to_delete


def open_export(index: int) -> tuple[bool, str]:
    """
    Open an export file in the default editor.

    Args:
        index: 1-based index of the export to open

    Returns:
        Tuple of (success, message)
    """
    exports = get_exports()

    if not exports:
        return False, "No exports found"

    if index < 1 or index > len(exports):
        return False, f"Invalid index. Valid range: 1-{len(exports)}"

    export_path = exports[index - 1]["path"]

    # Determine the editor
    editor = os.environ.get("EDITOR", os.environ.get("VISUAL", ""))

    if not editor:
        # Platform-specific defaults
        if sys.platform == "darwin":
            editor = "open"
        elif sys.platform == "win32":
            editor = "notepad"
        else:
            editor = "xdg-open"

    try:
        subprocess.run([editor, str(export_path)], check=True)
        return True, f"Opened {export_path.name}"
    except subprocess.CalledProcessError as e:
        return False, f"Failed to open file: {e}"
    except FileNotFoundError:
        return False, f"Editor not found: {editor}"


def get_total_size() -> tuple[int, str]:
    """
    Get total size of all exports.

    Returns:
        Tuple of (size_bytes, size_human)
    """
    exports = get_exports()
    total = sum(e["size"] for e in exports)
    return total, format_size(total)


def delete_export(index: int) -> tuple[bool, str]:
    """
    Delete a specific export by index.

    Args:
        index: 1-based index of the export to delete

    Returns:
        Tuple of (success, message)
    """
    exports = get_exports()

    if not exports:
        return False, "No exports found"

    if index < 1 or index > len(exports):
        return False, f"Invalid index. Valid range: 1-{len(exports)}"

    export_path = exports[index - 1]["path"]

    try:
        export_path.unlink()
        return True, f"Deleted {export_path.name}"
    except IOError as e:
        return False, f"Failed to delete: {e}"
