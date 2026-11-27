#!/usr/bin/env python3
# Receives a stop/end-of-turn hook event and prompts the agent once to capture
# unrecorded learnings after N turns without a knowledge-base write. Fails open
# (outputs nothing on error). Uses Python 3.11+ standard library only.
#
# Example: python3 capture_nudge.py <claude-code|antigravity> (antigravity covers App, IDE, and CLI)
# Env var PK_CAPTURE_NUDGE_TURNS: turn threshold before nudging (default: 10)

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

REASON = (
    "If you gained any general-purpose learnings during this session (unexpected tool behavior, "
    "user feedback or policies, chosen decisions, or disproven assumptions) that have not yet been "
    "recorded in the knowledge base, capture them as event logs using the knowledge-capture workflow. "
    "Environment-specific or engagement-specific facts belong in built-in agent memory instead. "
    "If there is nothing to record, finish without taking further action."
)
WRITE_TOOL_PATTERN = re.compile(r"bm_write|bm_edit")
SESSION_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
STATE_KEYS = ("stops", "lastResetStop", "writes")


def count_writes(transcript_path: Any) -> int:
    """Count occurrences of knowledge-base write tool names in the transcript, or 0 if unreadable."""
    if not isinstance(transcript_path, str) or transcript_path == "":
        return 0
    path = Path(transcript_path)
    try:
        if not path.is_file():
            return 0
        with path.open("r", encoding="utf-8", errors="replace") as fh:
            return sum(len(WRITE_TOOL_PATTERN.findall(line)) for line in fh)
    except OSError:
        return 0


def next_state(state: dict[str, int], writes: int, threshold: int) -> tuple[dict[str, int], bool]:
    """Advance state by one stop event and return (updated_state, should_nudge)."""
    state = {**state, "stops": state["stops"] + 1}
    if writes > state["writes"]:
        return {**state, "writes": writes, "lastResetStop": state["stops"]}, False
    if state["stops"] - state["lastResetStop"] >= threshold:
        return {**state, "lastResetStop": state["stops"]}, True
    return state, False


def _read_stdin() -> Any:
    try:
        return json.loads(sys.stdin.buffer.read().decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None


def _state_dir() -> Path:
    xdg = os.environ.get("XDG_STATE_HOME", "")
    state_home = Path(xdg) if xdg and Path(xdg).is_absolute() else (Path.home() / ".local" / "state")
    return state_home / "personal-knowledge" / "capture-nudge"


def _load_state(state_path: Path) -> dict[str, int]:
    state = {"stops": 0, "lastResetStop": 0, "writes": 0}
    try:
        loaded = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return state
    if not isinstance(loaded, dict):
        return state
    for key in STATE_KEYS:
        val = loaded.get(key)
        if isinstance(val, int) and not isinstance(val, bool) and val >= 0:
            state[key] = val
    return state


def _save_state_atomic(state_dir: Path, state_path: Path, state: dict[str, int]) -> None:
    state_dir.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(state_dir, 0o700)
    except OSError:
        pass
    tmp_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=state_dir,
            prefix=f".{state_path.name}.",
            suffix=".tmp",
            mode="w",
            encoding="utf-8",
            delete=False,
        ) as tmp_file:
            tmp_name = tmp_file.name
            tmp_file.write(json.dumps(state))
        os.replace(tmp_name, state_path)
    except Exception:
        if tmp_name is not None:
            try:
                Path(tmp_name).unlink(missing_ok=True)
            except OSError:
                pass
        raise


def main(argv: list[str]) -> None:
    product = argv[1] if len(argv) > 1 else None
    data = _read_stdin()
    if not isinstance(data, dict):
        return

    if product == "claude-code":
        if data.get("stop_hook_active") is True:
            return
        session_id = data.get("session_id")
        transcript_path = data.get("transcript_path")
    elif product == "antigravity":
        session_id = data.get("conversationId")
        transcript_path = data.get("transcriptPath")
    else:
        return
    if not isinstance(session_id, str) or SESSION_ID.match(session_id) is None:
        return

    try:
        threshold = int(os.environ.get("PK_CAPTURE_NUDGE_TURNS", "10"))
    except ValueError:
        return
    if threshold < 1:
        return

    state_dir = _state_dir()
    state_path = state_dir / f"{session_id}.json"
    state = _load_state(state_path)

    state, nudge = next_state(state, count_writes(transcript_path), threshold)
    _save_state_atomic(state_dir, state_path, state)
    if nudge:
        decision = "block" if product == "claude-code" else "continue"
        sys.stdout.buffer.write(json.dumps({"decision": decision, "reason": REASON}, ensure_ascii=False).encode("utf-8"))
        sys.stdout.buffer.flush()


if __name__ == "__main__":
    try:
        main(sys.argv)
    except Exception:
        # Fail open on unexpected errors
        pass
