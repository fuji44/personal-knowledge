# Client Setup

This guide covers connecting AI clients from **Anthropic**, **Google**, and **OpenAI** to your Basic Memory MCP server, grouped by form factor (**Terminal**, **Desktop**, and **Web**).

## Support Matrix

| Category | Vendor | Client | Integration | Hooks (`frontmatter_guard` / `capture_nudge`) | Status |
| --- | --- | --- | --- | --- | --- |
| **Terminal** | Anthropic | **Claude Code** | Full Plugin | Yes (`PreToolUse`, `PostToolUse`, `Stop`) | Verified (Linux / WSL2) |
| **Terminal** | Google | **Antigravity CLI** | Full Plugin | Yes (`PreToolUse`, `Stop`) | Verified (Linux / WSL2) |
| **Terminal** | OpenAI | **Codex CLI** | MCP Only | No | Unverified |
| **Desktop** | Anthropic | **Claude Desktop** (Code tab) | Full Plugin | Yes (shares Claude Code engine) | Supported (unverified) |
| **Desktop** | Anthropic | **Claude Desktop** (Chat tab) | MCP Only | No | MCP only |
| **Desktop** | Google | **Antigravity App / IDE** | Full Plugin | Yes (`PreToolUse`, `Stop`) | Verified (Linux / WSL2) |
| **Desktop** | OpenAI | **ChatGPT Desktop** | MCP Only | No | Unverified |
| **Web** | Anthropic | **claude.ai** | MCP Only (remote) | No | MCP only |
| **Web** | OpenAI | **ChatGPT** | MCP Only (remote) | No | Unverified |
| **Web** | Google | **Gemini** | Limited | No | Consumer Web limited; Enterprise / Agent Platform supports remote MCP |

> [!TIP]
> **Advice for MCP-Only Clients (Read-Only Usage Recommended)**
> Clients connected via MCP only can technically write notes, but because lifecycle hooks (`frontmatter_guard.py`) and plugin rules do not run there, writes are not checked against your closed vocabulary and schema. To avoid polluting your knowledge base with malformed notes, consider using MCP-only clients primarily in a **read-only** workflow (searching and reading existing notes) and performing structured writes from a Full Plugin client.

---

## Terminal Clients

### Claude Code (Anthropic)

- **Default localhost endpoint (`http://localhost:48000/mcp`)**:
  ```text
  /plugin marketplace add ./
  /plugin install personal-knowledge@personal-knowledge
  ```
  Or launch directly from the repository without marketplace registration:
  ```bash
  claude --plugin-dir ./plugins/personal-knowledge
  ```
- **Custom or remote endpoint**: Generate a tailored plugin directory first with [build-local-plugin.sh](../../scripts/build-local-plugin.sh):
  ```bash
  ./scripts/build-local-plugin.sh "https://bm.example.com/mcp" "./dist/personal-knowledge"
  claude --plugin-dir ./dist/personal-knowledge
  ```

### Antigravity CLI (Google)

Antigravity CLI shares the same plugin directory as Antigravity App and IDE. See [Antigravity App / IDE](#antigravity-app--ide-google) below.

### Codex CLI (OpenAI — MCP Only)

Register the Basic Memory Streamable HTTP endpoint using `codex mcp add` (or `~/.codex/config.toml`):

```bash
codex mcp add basic-memory --url http://localhost:48000/mcp
```

For remote endpoints, authentication flags, and current configuration syntax, refer to the official OpenAI Codex CLI MCP documentation.

---

## Desktop Clients

### Claude Desktop (Anthropic)

- **Code tab**: Shares the Claude Code engine and supports the full plugin workflow.
- **Chat tab**: Connects as an MCP-only client. Add your local or remote MCP URL (`https://bm.example.com/mcp`) in Claude Desktop's MCP / Connectors settings.

### Antigravity App / IDE (Google)

*(Applies to Antigravity App, IDE, and CLI.)*

- **Default localhost endpoint (`http://localhost:48000/mcp`)**:
  ```bash
  mkdir -p ~/.gemini/config/plugins
  ln -s "$(pwd)/plugins/personal-knowledge" ~/.gemini/config/plugins/personal-knowledge
  ```
- **Custom or remote endpoint**: Antigravity's `mcp_config.json` does not expand environment variables in URLs. Generate a tailored plugin directory with [build-local-plugin.sh](../../scripts/build-local-plugin.sh):
  ```bash
  ./scripts/build-local-plugin.sh "https://bm.example.com/mcp" "$HOME/.gemini/config/plugins/personal-knowledge"
  ```
  *(Remove any existing symlink at the target path first; `build-local-plugin.sh` intentionally refuses to overwrite a symlink.)*

Restart Antigravity after installing or updating the plugin.

### ChatGPT Desktop (OpenAI — MCP Only)

Configure a custom MCP server / connector pointing to your endpoint (availability depends on your ChatGPT plan; refer to OpenAI's official MCP connector documentation for current UI steps).

---

## Web Clients

Web clients cannot reach `localhost` directly; expose your server securely over HTTPS with OAuth first (see [Local Host + Cloudflare](./cloudflare-remote.md)).

- **claude.ai (Anthropic)**: Add `https://bm.example.com/mcp` as a Custom Connector in Settings and complete the OAuth login prompt.
- **ChatGPT (OpenAI)**: Add `https://bm.example.com/mcp` as a remote MCP connector where supported by your plan.
- **Gemini (Google)**: Consumer `gemini.google.com` does not generally allow arbitrary third-party remote MCP URLs. For enterprise environments, refer to Google Cloud's Gemini Enterprise / Agent Platform remote MCP documentation.
