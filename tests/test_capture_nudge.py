import json
import subprocess
import sys
import tempfile
import unittest
import uuid
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "plugins" / "personal-knowledge" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from capture_nudge import count_writes, next_state  # noqa: E402

INITIAL = {"stops": 0, "lastResetStop": 0, "writes": 0}


class NextStateTest(unittest.TestCase):
    def test_nudges_once_after_threshold_without_writes(self):
        state = INITIAL
        results = []
        for _ in range(4):
            state, nudge = next_state(state, 0, 2)
            results.append(nudge)
        self.assertEqual(results, [False, True, False, True])

    def test_new_write_resets_the_count(self):
        state, _ = next_state(INITIAL, 0, 2)
        state, nudge = next_state(state, 1, 2)
        self.assertFalse(nudge)
        self.assertEqual(state, {"stops": 2, "lastResetStop": 2, "writes": 1})
        state, nudge = next_state(state, 1, 2)
        self.assertFalse(nudge)
        state, nudge = next_state(state, 1, 2)
        self.assertTrue(nudge)


class CountWritesTest(unittest.TestCase):
    def test_counts_tool_names(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "t.jsonl"
            path.write_text('{"name":"bm_write"}\n{"name":"bm_read"}\n{"name":"bm_edit"}\n', encoding="utf-8")
            self.assertEqual(count_writes(str(path)), 2)
            self.assertEqual(count_writes(d), 0)
        self.assertEqual(count_writes("/nonexistent"), 0)
        self.assertEqual(count_writes(None), 0)


class CommandTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.state_home = str(Path(self._tmp.name) / "state")

    def run_hook(self, product, payload, turns="2"):
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "capture_nudge.py"), product],
            input=json.dumps(payload).encode("utf-8"),
            capture_output=True,
            env={
                "PK_CAPTURE_NUDGE_TURNS": turns,
                "XDG_STATE_HOME": self.state_home,
                "TMPDIR": self._tmp.name,
                "PATH": "/usr/bin:/bin",
            },
        )
        self.assertEqual(result.returncode, 0)
        out = result.stdout.decode("utf-8")
        return None if out == "" else json.loads(out)

    def test_claude_code_blocks_on_threshold(self):
        payload = {"session_id": f"test-{uuid.uuid4()}", "transcript_path": "/nonexistent"}
        self.assertIsNone(self.run_hook("claude-code", payload))
        self.assertEqual(self.run_hook("claude-code", payload)["decision"], "block")
        self.assertIsNone(self.run_hook("claude-code", {**payload, "stop_hook_active": True}))

    def test_antigravity_continues_on_threshold(self):
        payload = {"conversationId": f"test-{uuid.uuid4()}", "transcriptPath": "/nonexistent"}
        self.assertIsNone(self.run_hook("antigravity", payload))
        self.assertEqual(self.run_hook("antigravity", payload)["decision"], "continue")

    def test_rejects_unsafe_session_id(self):
        self.assertIsNone(self.run_hook("claude-code", {"session_id": "../x"}, turns="1"))
        self.assertIsNone(self.run_hook("claude-code", {"session_id": "."}, turns="1"))
        self.assertIsNone(self.run_hook("claude-code", {"session_id": "sess1\n"}, turns="1"))

    def test_ignores_invalid_threshold_and_corrupt_state(self):
        sid = f"test-{uuid.uuid4()}"
        payload = {"session_id": sid, "transcript_path": "/nonexistent"}
        self.assertIsNone(self.run_hook("claude-code", payload, turns="0"))
        self.assertIsNone(self.run_hook("claude-code", payload, turns="abc"))

        state_file = Path(self.state_home) / "personal-knowledge" / "capture-nudge" / f"{sid}.json"
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text('["not", "a", "dict"]', encoding="utf-8")
        self.assertEqual(self.run_hook("claude-code", payload, turns="1")["decision"], "block")


if __name__ == "__main__":
    unittest.main()
