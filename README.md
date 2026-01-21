# claude-compact

Customize Claude Code's compaction experience by automatically exporting full conversations before compaction and injecting context pointers afterward.

## The Problem

When Claude Code compacts your conversation (at ~95% context), the built-in summary often loses critical details:
- File paths and code changes
- Error messages and debugging steps
- Architectural decisions and their rationale
- Tool call inputs and outputs

## The Solution

`claude-compact` installs hooks that:
1. **Before compaction**: Export the full conversation to a readable markdown file
2. **After compaction**: Tell Claude where to find the exported file

Claude can then read the full conversation history when needed, preserving all context.

## Installation

```bash
pip install claude-compact
```

Or install from source:

```bash
git clone https://github.com/yourusername/claude-code-compact-hook
cd claude-code-compact-hook
pip install -e .
```

### Dependencies

This tool requires `claude-conversation-extractor` for exporting conversations:

```bash
pip install claude-conversation-extractor
```

## Quick Start

```bash
# Install the hooks
claude-compact install

# Check status
claude-compact status

# That's it! Now when Claude Code compacts, your conversations are preserved.
```

## Commands

### Installation

```bash
claude-compact install    # Install hooks into Claude Code
claude-compact uninstall  # Remove hooks
claude-compact status     # Check installation status
```

### Configuration

```bash
claude-compact config show          # Show all settings
claude-compact config set KEY VALUE # Set a configuration value
claude-compact config reset         # Reset to defaults
```

**Available settings:**

| Setting | Default | Description |
|---------|---------|-------------|
| `export_dir` | `~/.claude/hooks/exports` | Where to save exports |
| `export_format` | `markdown` | Format: markdown, json, html |
| `detailed` | `true` | Include tool calls in export |
| `trigger` | `*` | Hook trigger: `auto`, `manual`, or `*` (both) |
| `cleanup_enabled` | `true` | Auto-cleanup old exports |
| `cleanup_mode` | `age` | Cleanup by `age` or `count` |
| `cleanup_max_age_days` | `30` | Delete exports older than N days |
| `cleanup_max_count` | `50` | Keep only N most recent exports |

### Exports Management

```bash
claude-compact exports list         # List all exports
claude-compact exports list -n 10   # List last 10 exports
claude-compact exports clean        # Clean based on config
claude-compact exports clean -d 7   # Delete exports older than 7 days
claude-compact exports clean -k 20  # Keep only 20 most recent
claude-compact exports open 1       # Open most recent export in editor
```

### Prompt Customization

Customize the message Claude sees after compaction:

```bash
claude-compact prompt show    # Show current template
claude-compact prompt set     # Edit template (opens editor)
claude-compact prompt reset   # Reset to default
```

**Default template:**
```
IMPORTANT: This conversation was compacted. The FULL conversation before compaction is saved at:
{export_path}

If you need details from earlier in the conversation (file paths, error messages, code changes, tool calls, decisions made, etc.), use the Read tool to read that file.
```

**Available variables:**
- `{export_path}` - Full path to the exported file
- `{session_id}` - Session ID
- `{timestamp}` - Export timestamp

## How It Works

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Context fills up (~95%)                                  │
├─────────────────────────────────────────────────────────────┤
│ 2. PreCompact hook fires                                    │
│    → Runs claude-extract to export full conversation        │
│    → Saves export path for later                            │
├─────────────────────────────────────────────────────────────┤
│ 3. Claude Code compacts (normal behavior)                   │
├─────────────────────────────────────────────────────────────┤
│ 4. SessionStart hook fires                                  │
│    → Outputs continuation prompt to stdout                  │
│    → Claude sees: "Full conversation saved at <path>"       │
├─────────────────────────────────────────────────────────────┤
│ 5. You continue working                                     │
│    → Claude can read the export file if needed              │
└─────────────────────────────────────────────────────────────┘
```

## File Locations

- **Hooks**: `~/.claude/hooks/claude-compact-*.py`
- **Config**: `~/.claude/hooks/claude-compact-config.json`
- **Exports**: `~/.claude/hooks/exports/` (configurable)
- **Claude settings**: `~/.claude/settings.json`

## Troubleshooting

### Hooks not running?

1. Check installation: `claude-compact status`
2. Verify settings.json has the hooks: `cat ~/.claude/settings.json | grep claude-compact`
3. Try reinstalling: `claude-compact uninstall && claude-compact install`

### Export not created?

1. Ensure `claude-conversation-extractor` is installed: `pip install claude-conversation-extractor`
2. Check if you can run it manually: `claude-extract --list`

### Claude doesn't see the context?

The injected context is invisible to you but visible to Claude. Ask Claude: "Do you see any context about an exported conversation?"

## Uninstalling

```bash
# Remove hooks from Claude Code
claude-compact uninstall

# Optionally remove the package
pip uninstall claude-compact

# Optionally clean up exports
rm -rf ~/.claude/hooks/exports
rm ~/.claude/hooks/claude-compact-*.py
rm ~/.claude/hooks/claude-compact-config.json
```

## License

MIT

## Contributing

Contributions welcome! Please open an issue or PR.
