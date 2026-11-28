# Client Setup

This guide covers connecting AI clients to your Basic Memory MCP server, grouped by support level:

- **[Full Support (Plugin + Hooks)](#full-support-plugin--hooks)** — Recommended for daily reading and writing.
- **[MCP Only (Read-Only Recommended)](#mcp-only-read-only-recommended)** — Connects to MCP tools without plugin hooks or rules.
- **[Limited](#limited)** — Restricted custom remote MCP support for personal use.

---

## Full Support (Plugin + Hooks)

These clients run the full `personal-knowledge` plugin—MCP tools, project-scoping rules, lifecycle skills, and schema-enforcement hooks (`frontmatter_guard.py`, `capture_nudge.py`). Use one of these as your primary environment for structured writes.

| Client | Form Factor | Vendor | Hooks | Status |
| --- | --- | --- | --- | --- |
| **Claude Code** | Terminal | Anthropic | `PreToolUse`, `PostToolUse`, `Stop` | Verified (Linux / WSL2) |
| **Antigravity CLI** | Terminal | Google | `PreToolUse`, `Stop` | Verified (Linux / WSL2) |
| **Antigravity App** | Desktop | Google | `PreToolUse`, `Stop` | Verified (Linux / WSL2) |
| **Claude Desktop (Code tab)** | Desktop | Anthropic | Shares Claude Code engine | Supported (unverified) |

### Claude Code

Install directly from GitHub (no `git clone` required):

```bash
claude plugin marketplace add fuji44/personal-knowledge
claude plugin install personal-knowledge@personal-knowledge --config basic_memory_mcp_url=http://localhost:48000/mcp
```

Replace the `--config` URL with `https://bm.example.com/mcp` when connecting to a remote server.

### Antigravity CLI

Install directly from the GitHub repository URL (no `git clone` required; the full `https://` URL is required):

```bash
agy plugin install https://github.com/fuji44/personal-knowledge
```

The plugin installs disabled until its MCP URL is configured. Open `/plugin` inside `agy`, turn on `personal-knowledge`, and enter your **Basic Memory MCP server URL** (`http://localhost:48000/mcp` or `https://bm.example.com/mcp`).

### Antigravity App

Place the plugin under `~/.gemini/config/plugins/personal-knowledge` from a local clone:

```bash
git clone https://github.com/fuji44/personal-knowledge.git
mkdir -p ~/.gemini/config/plugins
ln -s "$(pwd)/personal-knowledge/plugins/personal-knowledge" ~/.gemini/config/plugins/personal-knowledge
```

Restart Antigravity App, open **Customizations > Installed**, enter your **Basic Memory MCP server URL** (`http://localhost:48000/mcp` or `https://bm.example.com/mcp`), and enable the plugin.

### Claude Desktop (Code tab)

Shares the Claude Code engine and supports the same plugin workflow.

---

## MCP Only (Read-Only Recommended)

> [!TIP]
> **Use MCP-only clients primarily as read-only.**
> Clients connected via MCP only can technically write notes, but because lifecycle hooks (`frontmatter_guard.py`) and plugin rules do not run there, writes are not checked against your closed vocabulary and schema. To avoid polluting your knowledge base with malformed notes, use these clients for searching and reading existing notes, and perform structured writes from a Full Support client.

| Client | Form Factor | Vendor | Endpoint Type | Status |
| --- | --- | --- | --- | --- |
| **Claude Desktop (Chat tab)** | Desktop | Anthropic | Local or remote HTTP | MCP only |
| **claude.ai** | Web | Anthropic | Remote HTTPS + OAuth | MCP only |

*(For remote HTTPS + OAuth setup, see [Local Host + Cloudflare](./cloudflare-remote.md).)*

- **Claude Desktop (Chat tab) / claude.ai**: Add your local or remote MCP URL (`https://bm.example.com/mcp`) under MCP / Custom Connectors in Settings.

---

## Limited

| Client | Form Factor | Vendor | Notes |
| --- | --- | --- | --- |
| **Gemini** | Web | Google | Consumer `gemini.google.com` does not generally allow arbitrary third-party remote MCP URLs. For enterprise environments, refer to Google Cloud's Gemini Enterprise / Agent Platform remote MCP documentation. |

---

## Optional: Installing from a Local Clone

If you are developing locally against a checked-out copy of this repository:

- **Claude Code**:
  ```bash
  claude plugin marketplace add ./
  claude plugin install personal-knowledge@personal-knowledge --config basic_memory_mcp_url=http://localhost:48000/mcp
  ```
- **Antigravity CLI**:
  ```bash
  agy plugin install ./plugins/personal-knowledge
  ```
