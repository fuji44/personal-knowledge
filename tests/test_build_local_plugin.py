import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "build-local-plugin.sh"


class BuildLocalPluginTest(unittest.TestCase):
    def test_builds_plugin_with_custom_url(self):
        target_url = "http://192.168.1.100:48000/mcp"
        with tempfile.TemporaryDirectory() as d:
            out_dir = Path(d) / "personal-knowledge"
            res = subprocess.run(
                ["bash", str(SCRIPT), target_url, str(out_dir)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(res.returncode, 0, res.stderr)

            mcp_config = json.loads((out_dir / "mcp_config.json").read_text(encoding="utf-8"))
            self.assertEqual(mcp_config["mcpServers"]["basic-memory"], {"serverUrl": target_url})

            mcp_json = json.loads((out_dir / "mcp.json").read_text(encoding="utf-8"))
            self.assertEqual(mcp_json["mcpServers"]["basic-memory"]["url"], target_url)

            claude_mcp = json.loads((out_dir / ".mcp.json").read_text(encoding="utf-8"))
            self.assertEqual(claude_mcp["mcpServers"]["basic-memory"]["url"], target_url)

            short_sha = subprocess.check_output(
                ["git", "-C", str(REPO_ROOT), "rev-parse", "--short", "HEAD"],
                text=True,
            ).strip()
            src_version = json.loads(
                (REPO_ROOT / "plugins" / "personal-knowledge" / "plugin.json").read_text(encoding="utf-8")
            )["version"]
            expected_version = f"{src_version}+local.{short_sha}"

            built_plugin = json.loads((out_dir / "plugin.json").read_text(encoding="utf-8"))
            self.assertEqual(built_plugin["version"], expected_version)
            built_claude_plugin = json.loads(
                (out_dir / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
            )
            self.assertEqual(built_claude_plugin["version"], expected_version)

            self.assertTrue((out_dir / "skills" / "personal-knowledge" / "SKILL.md").is_file())

    def test_builds_plugin_from_env_var(self):
        target_url = "http://192.168.1.200:48000/mcp"
        with tempfile.TemporaryDirectory() as d:
            out_dir = Path(d) / "personal-knowledge"
            env = {**os.environ, "BASIC_MEMORY_MCP_URL": target_url}
            res = subprocess.run(
                ["bash", str(SCRIPT), "", str(out_dir)],
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(res.returncode, 0, res.stderr)

            mcp_config = json.loads((out_dir / "mcp_config.json").read_text(encoding="utf-8"))
            self.assertEqual(mcp_config["mcpServers"]["basic-memory"], {"serverUrl": target_url})
            mcp_json = json.loads((out_dir / "mcp.json").read_text(encoding="utf-8"))
            self.assertEqual(mcp_json["mcpServers"]["basic-memory"]["url"], target_url)
            claude_mcp = json.loads((out_dir / ".mcp.json").read_text(encoding="utf-8"))
            self.assertEqual(claude_mcp["mcpServers"]["basic-memory"]["url"], target_url)

    def test_rejects_invalid_url_and_source_dir_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            res_bad_url = subprocess.run(
                ["bash", str(SCRIPT), "ftp://example.com/mcp", d],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(res_bad_url.returncode, 0)

            res_same_dir = subprocess.run(
                ["bash", str(SCRIPT), "http://192.168.1.100:48000/mcp", str(REPO_ROOT / "plugins" / "personal-knowledge")],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(res_same_dir.returncode, 0)

            res_parent_dir = subprocess.run(
                ["bash", str(SCRIPT), "http://192.168.1.100:48000/mcp", str(REPO_ROOT)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(res_parent_dir.returncode, 0)

            target_dir = Path(d) / "real-dir"
            target_dir.mkdir()
            (target_dir / "keep.txt").write_text("keep", encoding="utf-8")
            sym_dest = Path(d) / "sym-out"
            sym_dest.symlink_to(target_dir)
            res_symlink = subprocess.run(
                ["bash", str(SCRIPT), "http://192.168.1.100:48000/mcp", str(sym_dest)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(res_symlink.returncode, 0)
            self.assertTrue((target_dir / "keep.txt").is_file())

    def test_help_exits_zero(self):
        res = subprocess.run(["bash", str(SCRIPT), "--help"], capture_output=True, text=True, check=False)
        self.assertEqual(res.returncode, 0)
        self.assertIn("Usage:", res.stderr)


if __name__ == "__main__":
    unittest.main()
