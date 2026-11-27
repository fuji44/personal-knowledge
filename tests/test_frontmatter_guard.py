import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "plugins" / "personal-knowledge" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from frontmatter_guard import find_violations, load_projects, parse_frontmatter, write_tool_kind  # noqa: E402

VOCABULARY = json.loads((SCRIPTS.parent / "vocabulary.json").read_text(encoding="utf-8"))
ABSENT = {"state": "absent"}
LOADED = {"state": "loaded", "path": "/cfg/projects.json", "projects": ["acme"]}


def note(frontmatter: str) -> str:
    return f"---\n{frontmatter}\n---\n\n# Body\n"


VALID_LOG = note("title: x\ntype: log\ntags:\n- git\norigin:\n  kind: work\n  project: acme")
BASE = "title: x\ntags:\n- git\norigin:\n  kind: personal\n  project: null"


class ParseFrontmatterTest(unittest.TestCase):
    def test_block_list_nested_map_and_null(self):
        self.assertEqual(
            parse_frontmatter(VALID_LOG),
            {"title": "x", "type": "log", "tags": ["git"], "origin": {"kind": "work", "project": "acme"}},
        )
        self.assertEqual(
            parse_frontmatter(note("origin:\n  kind: personal\n  project: null"))["origin"],
            {"kind": "personal", "project": None},
        )

    def test_flow_list_map_and_quotes(self):
        parsed = parse_frontmatter(note("tags: [git, 'github']\norigin: {kind: external, project: null}"))
        self.assertEqual(parsed, {"tags": ["git", "github"], "origin": {"kind": "external", "project": None}})

    def test_list_of_maps(self):
        parsed = parse_frontmatter(note("promoted_to:\n- kind: skill\n  repo: r\n  path: p\n- kind: hook\n  repo: r2\n  path: p2"))
        self.assertEqual(
            parsed["promoted_to"],
            [{"kind": "skill", "repo": "r", "path": "p"}, {"kind": "hook", "repo": "r2", "path": "p2"}],
        )

    def test_no_frontmatter(self):
        self.assertIsNone(parse_frontmatter("# Heading only\n"))

    def test_inline_comments_bom_crlf_and_unhashable_key(self):
        raw = "\ufeff---\r\ntype: log # event log\r\ntags: [git] # closed tag\r\norigin: # nested\r\n  kind: personal\r\n  project: null\r\n[]: ignored\r\n---\r\n\r\n# Body\r\n"
        parsed = parse_frontmatter(raw)
        self.assertEqual(
            parsed,
            {"type": "log", "tags": ["git"], "origin": {"kind": "personal", "project": None}, "[]": "ignored"},
        )
        self.assertEqual(find_violations("write", {"content": raw}, VOCABULARY, ABSENT), [])

    def test_deep_flow_brackets_and_block_scalar_do_not_bypass(self):
        deep = "[" * 1500 + "git" + "]" * 1500
        violations = find_violations("write", {"content": note(BASE.replace("- git", f" {deep}"))}, VOCABULARY, ABSENT)
        self.assertTrue(violations)

        with_block_scalar = note(BASE + "\ntype: practice\nsummary: |\n  line1\n  line2\nstatus: established")
        self.assertEqual(
            find_violations("write", {"content": with_block_scalar}, VOCABULARY, ABSENT),
            ['status "established" is not in vocabulary for type "practice"'],
        )


class FindViolationsWriteTest(unittest.TestCase):
    def check(self, args, expected, projects=ABSENT):
        self.assertEqual(find_violations("write", args, VOCABULARY, projects), expected)

    def test_valid(self):
        self.check({"content": VALID_LOG}, [], LOADED)

    def test_tag_outside_vocabulary(self):
        self.check({"content": VALID_LOG.replace("- git", "- git\n- frontmatter")}, ['tag "frontmatter" is not in vocabulary'])

    def test_tags_param_and_metadata(self):
        self.check(
            {"content": VALID_LOG, "tags": "git,unknown", "metadata": {"origin": {"kind": "hobby", "project": None}}},
            ['origin.kind "hobby" is not in vocabulary', 'tag "unknown" is not in vocabulary'],
        )

    def test_missing_type_falls_back_to_note_type(self):
        content = note(BASE)
        self.check({"content": content}, ['type "note" is not in vocabulary'])
        self.check({"content": content, "note_type": "log"}, [])

    def test_status_by_type(self):
        self.check(
            {"content": note(BASE + "\ntype: practice\nstatus: established")},
            ['status "established" is not in vocabulary for type "practice"'],
        )
        self.check({"content": note(BASE + "\ntype: entity")}, ['notes of type "entity" require status'])
        self.check({"content": note(BASE + "\ntype: log\nstatus: tentative")}, ['notes of type "log" must not have status'])
        self.check({"content": note(BASE + "\ntype: log\nstatus: null")}, [])
        self.check({"content": note(BASE + "\ntype: concept\nstatus: null")}, ['notes of type "concept" require status'])

    def test_required_fields(self):
        self.check({"content": note("type: log")}, ["tags is required", "origin is required"])
        self.check(
            {"content": note("type: log\ntags: [git]\norigin:\n  kind: work")},
            ["origin.project is required (use null if not derived from a specific project)"],
        )

    def test_origin_project(self):
        other = VALID_LOG.replace("project: acme", "project: other")
        self.check({"content": other}, [])
        self.check({"content": other}, ['origin.project "other" is not in the environment list (/cfg/projects.json)'], LOADED)
        self.assertEqual(
            find_violations("write", {"content": VALID_LOG.replace("project: acme", "project: Acme Inc")}, VOCABULARY, ABSENT),
            ['origin.project "Acme Inc" is neither a slug (lowercase letters, digits, hyphens) nor null'],
        )
        self.check(
            {"content": VALID_LOG.replace("project: acme", 'project: "acme\\n"')},
            ['origin.project "acme\\\\n" is neither a slug (lowercase letters, digits, hyphens) nor null'],
        )
        self.check(
            {"content": VALID_LOG},
            ["origin.project list (/cfg/projects.json) cannot be read as a JSON array of strings"],
            {"state": "invalid", "path": "/cfg/projects.json"},
        )


class FindViolationsEditTest(unittest.TestCase):
    def test_only_metadata_is_checked(self):
        self.assertEqual(find_violations("edit", {"command": "append", "content": "- [fact] x"}, VOCABULARY, ABSENT), [])
        self.assertEqual(
            find_violations("edit", {"command": "set_metadata", "metadata": {"status": "adopted"}}, VOCABULARY, ABSENT), []
        )
        self.assertEqual(
            find_violations(
                "edit", {"command": "set_metadata", "metadata": {"tags": ["nope"], "status": "done"}}, VOCABULARY, ABSENT
            ),
            ['tag "nope" is not in vocabulary', 'status "done" is not in vocabulary for type "unknown"'],
        )


class WriteToolKindTest(unittest.TestCase):
    def test_tool_names(self):
        self.assertEqual(write_tool_kind("mcp__plugin_personal-knowledge_basic-memory__bm_write"), "write")
        self.assertEqual(write_tool_kind("mcp__plugin_personal-knowledge_basic-memory__bm_edit"), "edit")
        self.assertEqual(write_tool_kind("mcp_personal-knowledge_basic-memory_bm_write"), "write")
        self.assertEqual(write_tool_kind("bm_edit"), "edit")
        self.assertIsNone(write_tool_kind("mcp__plugin_personal-knowledge_basic-memory__bm_read"))
        self.assertIsNone(write_tool_kind("mcp_other_bm_write"))
        self.assertIsNone(write_tool_kind("xbm_write"))


class LoadProjectsTest(unittest.TestCase):
    def test_states(self):
        with tempfile.TemporaryDirectory() as d:
            path = str(Path(d) / "projects.json")
            self.assertEqual(load_projects({"PK_PROJECTS_FILE": path}), {"state": "absent"})
            Path(path).write_text("{", encoding="utf-8")
            self.assertEqual(load_projects({"PK_PROJECTS_FILE": path}), {"state": "invalid", "path": path})
            Path(path).write_text('["acme"]', encoding="utf-8")
            self.assertEqual(
                load_projects({"PK_PROJECTS_FILE": path}), {"state": "loaded", "path": path, "projects": ["acme"]}
            )
            self.assertEqual(load_projects({"XDG_CONFIG_HOME": d}), {"state": "absent"})


class CommandTest(unittest.TestCase):
    BAD_ARGS = {"project": "main", "content": VALID_LOG.replace("- git", "- nope")}

    def run_hook(self, args, payload):
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "frontmatter_guard.py"), *args],
            input=json.dumps(payload).encode("utf-8"),
            capture_output=True,
            env={"PK_PROJECTS_FILE": "/nonexistent/projects.json", "PATH": "/usr/bin:/bin"},
        )
        self.assertEqual(result.returncode, 0)
        out = result.stdout.decode("utf-8")
        return None if out == "" else json.loads(out)

    def test_claude_code_pre_denies(self):
        out = self.run_hook(
            ["claude-code", "pre"],
            {"tool_name": "mcp__plugin_personal-knowledge_basic-memory__bm_write", "tool_input": self.BAD_ARGS},
        )
        self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertIn('"nope"', out["hookSpecificOutput"]["permissionDecisionReason"])

    def test_claude_code_post_adds_context(self):
        out = self.run_hook(
            ["claude-code", "post"],
            {
                "tool_name": "mcp__plugin_personal-knowledge_basic-memory__bm_edit",
                "tool_input": {"project": "main", "identifier": "git", "command": "append", "content": "x"},
            },
        )
        self.assertIn(
            'bm_schema(command="validate", project="main", identifier="git")',
            out["hookSpecificOutput"]["additionalContext"],
        )

    def test_antigravity_call_mcp_tool(self):
        call = {"ServerName": "personal-knowledge_basic-memory", "ToolName": "bm_write", "Arguments": self.BAD_ARGS}
        self.assertEqual(
            self.run_hook(["antigravity", "pre"], {"toolCall": {"name": "call_mcp_tool", "args": call}})["decision"], "deny"
        )
        other = {**call, "ServerName": "other"}
        self.assertIsNone(self.run_hook(["antigravity", "pre"], {"toolCall": {"name": "call_mcp_tool", "args": other}}))

    def test_antigravity_direct_tool_and_post(self):
        tool_call = {"name": "mcp_personal-knowledge_basic-memory_bm_write", "args": self.BAD_ARGS}
        self.assertEqual(self.run_hook(["antigravity", "pre"], {"toolCall": tool_call})["decision"], "deny")
        self.assertIsNone(self.run_hook(["antigravity", "post"], {"toolCall": tool_call}))

    def test_no_output_when_valid(self):
        tool_call = {"name": "mcp_personal-knowledge_basic-memory_bm_write", "args": {"project": "main", "content": VALID_LOG}}
        self.assertIsNone(self.run_hook(["antigravity", "pre"], {"toolCall": tool_call}))

    def test_no_output_on_garbage(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "frontmatter_guard.py"), "claude-code", "pre"], input=b"garbage", capture_output=True
        )
        self.assertEqual((result.returncode, result.stdout), (0, b""))


if __name__ == "__main__":
    unittest.main()
