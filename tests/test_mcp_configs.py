import json
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PLUGIN_ROOT = REPO_ROOT / "plugins" / "personal-knowledge"
CONFIG_FILES = ("mcp_config.json", "mcp.json", ".mcp.json")


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
        for server_name in loaded["mcp_config.json"]:
            urls = {
                name: _extract_url(name, servers[server_name])
                for name, servers in loaded.items()
            }
            unique_urls = set(urls.values())
            self.assertEqual(len(unique_urls), 1, f"URL mismatch for {server_name}: {urls}")
            url = next(iter(unique_urls))
            self.assertEqual(url, "http://localhost:48000/mcp", f"Expected localhost default URL, got {url}")

    def test_config_schemas_match_client_expectations(self):
        mcp_json = _load_servers("mcp.json")
        for server_name, entry in mcp_json.items():
            self.assertEqual(entry.get("type"), "streamable-http", f"mcp.json[{server_name}]")
            self.assertIsInstance(entry.get("url"), str)

        claude_mcp = _load_servers(".mcp.json")
        for server_name, entry in claude_mcp.items():
            self.assertEqual(entry.get("type"), "http", f".mcp.json[{server_name}]")
            self.assertIsInstance(entry.get("url"), str)

        antigravity_mcp = _load_servers("mcp_config.json")
        for server_name, entry in antigravity_mcp.items():
            self.assertIsInstance(
                entry.get("serverUrl"),
                str,
                f"mcp_config.json[{server_name}] must use serverUrl without npx",
            )
            self.assertNotIn("command", entry, f"mcp_config.json[{server_name}] must not depend on command/npx")

    def test_skill_mentions_matching_endpoint_url(self):
        servers = _load_servers("mcp_config.json")
        skill_text = (PLUGIN_ROOT / "skills" / "personal-knowledge" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        for server_name, entry in servers.items():
            url = _extract_url("mcp_config.json", entry)
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
