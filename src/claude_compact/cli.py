"""CLI for claude-compact."""

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax

from . import __version__, config, exports, installer

console = Console()


@click.group()
@click.version_option(version=__version__)
def main():
    """Customize Claude Code's compaction experience.

    This tool installs hooks that automatically export your full conversation
    before compaction and inject a context pointer afterward, so Claude knows
    where to find the complete history.
    """
    pass


# === Install/Uninstall Commands ===


@main.command()
def install():
    """Install hooks into Claude Code."""
    with console.status("Installing hooks..."):
        success, message = installer.install_hooks()

    if success:
        console.print(f"[green]✓[/green] {message}")
        console.print()
        console.print("Hooks will now run when Claude Code compacts conversations.")
        console.print("Use [cyan]claude-compact status[/cyan] to verify installation.")
    else:
        console.print(f"[red]✗[/red] {message}")
        raise SystemExit(1)


@main.command()
def uninstall():
    """Remove hooks from Claude Code."""
    with console.status("Uninstalling hooks..."):
        success, message = installer.uninstall_hooks()

    if success:
        console.print(f"[green]✓[/green] {message}")
    else:
        console.print(f"[red]✗[/red] {message}")
        raise SystemExit(1)


@main.command()
def status():
    """Show installation status."""
    status_info = installer.get_status()

    if status_info["installed"]:
        console.print("[green]✓ Hooks are installed[/green]")
    else:
        console.print("[yellow]✗ Hooks are not installed[/yellow]")

    console.print()

    table = Table(show_header=False, box=None)
    table.add_column("Key", style="dim")
    table.add_column("Value")

    table.add_row("PreCompact hook", "✓" if status_info["precompact_hook_exists"] else "✗")
    table.add_row("SessionStart hook", "✓" if status_info["sessionstart_hook_exists"] else "✗")
    table.add_row("Settings file", status_info["settings_file"])
    table.add_row("Hooks directory", status_info["hooks_dir"])
    table.add_row("Config file", status_info["config_file"])
    table.add_row("Exports directory", status_info["exports_dir"])

    console.print(table)


# === Config Commands ===


@main.group(name="config")
def config_group():
    """Manage configuration."""
    pass


@config_group.command(name="show")
def config_show():
    """Show current configuration."""
    cfg = config.load_config()

    table = Table(title="Configuration", show_header=True)
    table.add_column("Setting", style="cyan")
    table.add_column("Value")
    table.add_column("Description", style="dim")

    descriptions = {
        "export_dir": "Directory for exports",
        "export_format": "Export format (markdown/json/html)",
        "detailed": "Include tool calls in export",
        "trigger": "Hook trigger (auto/manual/*)",
        "cleanup_enabled": "Enable auto-cleanup",
        "cleanup_mode": "Cleanup mode (age/count)",
        "cleanup_max_age_days": "Max age in days (if mode=age)",
        "cleanup_max_count": "Max exports to keep (if mode=count)",
        "prompt_template": "Continuation prompt template",
    }

    for key, value in cfg.items():
        if key == "prompt_template":
            value = f"{value[:50]}..." if len(value) > 50 else value
        table.add_row(key, str(value), descriptions.get(key, ""))

    console.print(table)


@config_group.command(name="set")
@click.argument("key")
@click.argument("value")
def config_set(key: str, value: str):
    """Set a configuration value."""
    valid_keys = list(config.DEFAULT_CONFIG.keys())

    if key not in valid_keys:
        console.print(f"[red]Invalid key: {key}[/red]")
        console.print(f"Valid keys: {', '.join(valid_keys)}")
        raise SystemExit(1)

    config.set_config_value(key, value)
    console.print(f"[green]✓[/green] Set {key} = {value}")

    # If trigger changed, remind to reinstall
    if key == "trigger":
        console.print("[yellow]Note: Run 'claude-compact install' to apply trigger changes[/yellow]")


@config_group.command(name="reset")
@click.confirmation_option(prompt="Reset all configuration to defaults?")
def config_reset():
    """Reset configuration to defaults."""
    config.reset_config()
    console.print("[green]✓[/green] Configuration reset to defaults")


# === Exports Commands ===


@main.group(name="exports")
def exports_group():
    """Manage exported conversations."""
    pass


@exports_group.command(name="list")
@click.option("--limit", "-n", default=20, help="Number of exports to show")
def exports_list(limit: int):
    """List exported conversations."""
    export_list = exports.get_exports()

    if not export_list:
        console.print("[yellow]No exports found[/yellow]")
        console.print(f"Exports directory: {config.get_export_dir()}")
        return

    total_size, total_human = exports.get_total_size()

    table = Table(title=f"Exports ({len(export_list)} files, {total_human} total)")
    table.add_column("#", style="dim", width=4)
    table.add_column("Filename")
    table.add_column("Size", justify="right")
    table.add_column("Date", style="dim")

    for i, export in enumerate(export_list[:limit], 1):
        table.add_row(
            str(i),
            export["name"],
            export["size_human"],
            export["mtime"].strftime("%Y-%m-%d %H:%M"),
        )

    console.print(table)

    if len(export_list) > limit:
        console.print(f"[dim]... and {len(export_list) - limit} more[/dim]")


@exports_group.command(name="clean")
@click.option("--older-than", "-d", type=int, help="Delete exports older than N days")
@click.option("--keep", "-k", type=int, help="Keep only N most recent exports")
@click.option("--dry-run", is_flag=True, help="Show what would be deleted without deleting")
def exports_clean(older_than: int, keep: int, dry_run: bool):
    """Clean up old exports."""
    to_delete = exports.clean_exports(
        older_than_days=older_than,
        keep_count=keep,
        dry_run=dry_run,
    )

    if not to_delete:
        console.print("[green]Nothing to clean[/green]")
        return

    action = "Would delete" if dry_run else "Deleted"

    for path in to_delete:
        console.print(f"[red]✗[/red] {action}: {path.name}")

    console.print()
    console.print(f"{action} {len(to_delete)} file(s)")


@exports_group.command(name="open")
@click.argument("index", type=int)
def exports_open(index: int):
    """Open an export in your editor."""
    success, message = exports.open_export(index)

    if success:
        console.print(f"[green]✓[/green] {message}")
    else:
        console.print(f"[red]✗[/red] {message}")
        raise SystemExit(1)


# === Prompt Commands ===


@main.group()
def prompt():
    """Customize the continuation prompt."""
    pass


@prompt.command(name="show")
def prompt_show():
    """Show current continuation prompt template."""
    template = config.get_prompt_template()

    console.print(Panel(
        template,
        title="Continuation Prompt Template",
        subtitle="Variables: {export_path}, {session_id}, {timestamp}",
    ))


@prompt.command(name="set")
@click.argument("template", required=False)
def prompt_set(template: str):
    """Set a custom continuation prompt template.

    If TEMPLATE is not provided, opens an editor to write the template.
    """
    if not template:
        # Use click's editor
        template = click.edit(config.get_prompt_template())
        if template is None:
            console.print("[yellow]Cancelled[/yellow]")
            return
        template = template.strip()

    if not template:
        console.print("[red]Template cannot be empty[/red]")
        raise SystemExit(1)

    config.set_prompt_template(template)
    console.print("[green]✓[/green] Prompt template updated")


@prompt.command(name="reset")
def prompt_reset():
    """Reset prompt template to default."""
    config.reset_prompt_template()
    console.print("[green]✓[/green] Prompt template reset to default")


if __name__ == "__main__":
    main()
