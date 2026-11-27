# Contributing

Thank you for your interest in `personal-knowledge`.

Because this repository is maintained primarily for personal knowledge-management workflows, please open an issue to discuss design changes before submitting large pull requests.

## Development Workflow

1. **Run the unit test suite** (uses Python 3.11+ standard library only):

   ```bash
   python3 -m unittest discover -s tests -v
   ```

2. **Keep MCP config files synchronized**:
   If you modify server names or endpoint URLs under [plugins/personal-knowledge/](plugins/personal-knowledge/), keep all three manifests (`mcp_config.json`, `mcp.json`, and `.mcp.json`) and [plugins/personal-knowledge/skills/personal-knowledge/SKILL.md](plugins/personal-knowledge/skills/personal-knowledge/SKILL.md) in sync. `tests/test_mcp_configs.py` verifies this automatically.

3. **Commit style**:
   Follow [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`).
