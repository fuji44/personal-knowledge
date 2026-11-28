import json
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PLUGIN_ROOT = REPO_ROOT / "plugins" / "personal-knowledge"
CONFIG_FILES = ("mcp_config.json", "mcp.json", ".claude-plugin/plugin.json")


def _load_servers(filename: str) -> dict:
    data = json.loads((PLUGIN_ROOT / filename).read_text(encoding="utf-8"))
    servers = data.get("mcpServers")
    if not isinstance(servers, dict) or not servers:
        raise AssertionError(f"{filename}: mcpServers must be a non-empty object")
    return servers


def _extract_url(filename: str, entry: dict) -> str:
    for key in ("serverUrl", "url"):
        val = entry.get(key)
        if isinstance(val, str) and val:
            return val
    raise AssertionError(f"{filename}: could not extract endpoint URL from {entry!r}")


class McpConfigsConsistencyTest(unittest.TestCase):
    def test_server_names_match_across_configs(self):
        loaded = {name: _load_servers(name) for name in CONFIG_FILES}
        key_sets = {name: set(servers.keys()) for name, servers in loaded.items()}
        expected = key_sets["mcp_config.json"]
        for name, keys in key_sets.items():
            self.assertEqual(keys, expected, f"{name} server names differ from mcp_config.json")

    def test_server_urls_match_across_configs(self):
        loaded = {name: _load_servers(name) for name in CONFIG_FILES}
        claude_manifest = json.loads((PLUGIN_ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        user_config = claude_manifest.get("userConfig")
        self.assertIsInstance(user_config, dict)
        url_cfg = user_config.get("basic_memory_mcp_url")
        self.assertIsInstance(url_cfg, dict)
        self.assertEqual(url_cfg.get("type"), "string")
        self.assertTrue(url_cfg.get("required"))

        for server_name in loaded["mcp_config.json"]:
            mcp_json_url = _extract_url("mcp.json", loaded["mcp.json"][server_name])
            self.assertEqual(
                mcp_json_url,
                "http://localhost:48000/mcp",
                f"Expected localhost default URL in mcp.json, got {mcp_json_url}",
            )

            claude_entry = loaded[".claude-plugin/plugin.json"][server_name]
            self.assertEqual(claude_entry.get("url"), "${user_config.basic_memory_mcp_url}")

            ag_entry = loaded["mcp_config.json"][server_name]
            self.assertEqual(ag_entry.get("url"), "${BASIC_MEMORY_MCP_URL}")
            variables = ag_entry.get("variables")
            self.assertIsInstance(variables, list)
            self.assertTrue(
                any(
                    isinstance(v, dict)
                    and v.get("name") == "BASIC_MEMORY_MCP_URL"
                    and isinstance(v.get("title"), str)
                    and isinstance(v.get("description"), str)
                    for v in variables
                ),
                f"mcp_config.json[{server_name}] must declare BASIC_MEMORY_MCP_URL variable",
            )

    def test_config_schemas_match_client_expectations(self):
        mcp_json = _load_servers("mcp.json")
        for server_name, entry in mcp_json.items():
            self.assertEqual(entry.get("type"), "streamable-http", f"mcp.json[{server_name}]")
            self.assertIsInstance(entry.get("url"), str)

        claude_mcp = _load_servers(".claude-plugin/plugin.json")
        for server_name, entry in claude_mcp.items():
            self.assertEqual(entry.get("type"), "http", f".claude-plugin/plugin.json[{server_name}]")
            self.assertIsInstance(entry.get("url"), str)

        antigravity_mcp = _load_servers("mcp_config.json")
        for server_name, entry in antigravity_mcp.items():
            self.assertIsInstance(
                entry.get("url"),
                str,
                f"mcp_config.json[{server_name}] must use url without npx",
            )
            self.assertNotIn("command", entry, f"mcp_config.json[{server_name}] must not depend on command/npx")

    def test_skill_mentions_matching_endpoint_url(self):
        servers = _load_servers("mcp.json")
        skill_text = (PLUGIN_ROOT / "skills" / "personal-knowledge" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        for server_name, entry in servers.items():
            url = _extract_url("mcp.json", entry)
            self.assertIn(url, skill_text, f"SKILL.md does not mention {server_name} URL {url}")

    def test_plugin_versions_match(self):
        marketplace = json.loads((REPO_ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
        plugin_json = json.loads((PLUGIN_ROOT / "plugin.json").read_text(encoding="utf-8"))
        claude_plugin_json = json.loads((PLUGIN_ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        versions = {
            marketplace["version"],
            marketplace["plugins"][0]["version"],
            plugin_json["version"],
            claude_plugin_json["version"],
        }
        self.assertEqual(len(versions), 1, f"Version mismatch across plugin manifests: {versions}")


if __name__ == "__main__":
    unittest.main()
