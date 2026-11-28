# AGENTS.md — AI Agent Operational & Editing Rules

This document defines operational conventions for AI agents editing this repository (`personal-knowledge`) and interacting with a personal knowledge base (`basic-memory` MCP server).

---

## 1. Knowledge Base (`basic-memory`) Scope Separation Rules

`basic-memory` separates projects by domain—such as personal hobby projects and client/work engagements (exact project names and structure are defined dynamically by each user's setup).

### Project Selection and Isolation Principles

1. **Always specify `project` explicitly:**
   - When calling `basic-memory` tools (`bm_write`, `bm_edit`, `bm_read`, `bm_search`, `bm_find`, `bm_list`, `bm_context`, etc.), always pass the **`project` parameter** corresponding to the current workspace or conversation context.
   - If the target project is ambiguous, ask the user before writing.
2. **Route by content, not by client machine:**
   - Knowledge that applies broadly across projects—including lessons learned at work once generalized by stripping proper nouns, internal identifiers, and confidential details—belongs in a shared general-purpose project regardless of which machine you connect from. Record the origin only as a slug in frontmatter (`origin.project`) to maintain a clear boundary for review and confidentiality. Learning from work is normal and should not be treated as an exception.
   - Information specific to a particular company or engagement belongs in that engagement's dedicated project. From a work machine, never read, search, or write to other clients' projects or private personal projects unless explicitly instructed by the user.
   - Never write confidential business data or proprietary code to any project outside its target engagement. If you are unsure whether an insight can be fully generalized, keep it out of the shared general-purpose project.

---

## 2. Plugin Editing & Verification Principles

1. **Why multiple MCP config files exist and keeping them synchronized:**
   - [plugins/personal-knowledge/](plugins/personal-knowledge/) defines MCP servers in three places for different client expectations (Antigravity reads `mcp_config.json` only and does not recognize `mcp.json` alone, so they cannot be consolidated into one file):
     - `mcp_config.json`: For Antigravity (App, CLI), using `${BASIC_MEMORY_MCP_URL}` via `variables`
     - `mcp.json`: For the Agent Plugins specification (`agent-plugins.org` schema)
     - `.claude-plugin/plugin.json`: For Claude Code plugins, using `${user_config.basic_memory_mcp_url}` via `userConfig`
   - Whenever you change the endpoint URL or server name, keep all three definitions and related skills synchronized, and verify consistency by running `python3 -m unittest discover -s tests -v`.
