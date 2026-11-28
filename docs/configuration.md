# Configuration

For supported AI clients and client-specific installation steps, see [Client Setup](./guides/clients.md).

## Remote or Custom Endpoint

Antigravity's `mcp_config.json` does not expand environment variables in endpoint URLs. To target a non-default port, LAN IP, or authenticated TLS/OAuth endpoint, generate a tailored plugin directory with [build-local-plugin.sh](../scripts/build-local-plugin.sh):

```bash
./scripts/build-local-plugin.sh "https://bm.example.com/mcp" "$HOME/.gemini/config/plugins/personal-knowledge"
```

You can also supply the endpoint via `BASIC_MEMORY_MCP_URL` (run `./scripts/build-local-plugin.sh --help` for full usage).

> [!IMPORTANT]
> If you expose `basic-memory` beyond `127.0.0.1`, place it behind an authenticating reverse proxy or Zero Trust Access layer (see [SECURITY.md](../SECURITY.md)). For a complete walkthrough using Cloudflare Tunnel and Cloudflare Access (Managed OAuth), see [Local Host + Cloudflare](./guides/cloudflare-remote.md).

## Customization

- **Closed Vocabulary**: Edit [vocabulary.json](../plugins/personal-knowledge/vocabulary.json) to adapt allowed `tags` and metadata vocabulary to your own domains and tech stack.
- **Per-Environment `origin.project` Allowlist**: Optionally create `$XDG_CONFIG_HOME/personal-knowledge/projects.json` (or set `PK_PROJECTS_FILE`) containing a JSON array of allowed project slugs (e.g., `["acme", "homelab"]`). When present, [frontmatter_guard.py](../plugins/personal-knowledge/scripts/frontmatter_guard.py) blocks writes with unlisted `origin.project` slugs.
- **Capture Nudge Threshold**: Set `PK_CAPTURE_NUDGE_TURNS` (default: `10`) to control how many turns without a knowledge-base write trigger [capture_nudge.py](../plugins/personal-knowledge/scripts/capture_nudge.py).
