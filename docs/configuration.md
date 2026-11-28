# Configuration

For supported AI clients and client-specific installation steps, see [Client Setup](./guides/clients.md).

## Remote or Custom Endpoint

Both Claude Code (`userConfig` in `.claude-plugin/plugin.json`) and Antigravity (`variables` in `mcp_config.json`) support configuring the Basic Memory MCP endpoint URL directly when installing or enabling the plugin—no custom build step is required. See [Client Setup](./guides/clients.md) for the commands.

> [!IMPORTANT]
> If you expose `basic-memory` beyond `127.0.0.1`, place it behind an authenticating reverse proxy or Zero Trust Access layer (see [SECURITY.md](../SECURITY.md)). For a complete walkthrough using Cloudflare Tunnel and Cloudflare Access (Managed OAuth), see [Local Host + Cloudflare](./guides/cloudflare-remote.md).

## Customization

- **Closed Vocabulary**: Edit [vocabulary.json](../plugins/personal-knowledge/vocabulary.json) to adapt allowed `tags` and metadata vocabulary to your own domains and tech stack.
- **Per-Environment `origin.project` Allowlist**: Optionally create `$XDG_CONFIG_HOME/personal-knowledge/projects.json` (or set `PK_PROJECTS_FILE`) containing a JSON array of allowed project slugs (e.g., `["acme", "homelab"]`). When present, [frontmatter_guard.py](../plugins/personal-knowledge/scripts/frontmatter_guard.py) blocks writes with unlisted `origin.project` slugs.
- **Capture Nudge Threshold**: Set `PK_CAPTURE_NUDGE_TURNS` (default: `10`) to control how many turns without a knowledge-base write trigger [capture_nudge.py](../plugins/personal-knowledge/scripts/capture_nudge.py).
