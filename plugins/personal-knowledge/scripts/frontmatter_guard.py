#!/usr/bin/env python3
# Intercepts knowledge-base write/edit tool calls. Before writing, denies writes
# whose frontmatter violates the closed vocabulary; after writing (claude-code only),
# injects context prompting observation/relation schema validation. Fails open
# (outputs nothing on error). Uses Python 3.11+ standard library only.
#
# Example: python3 frontmatter_guard.py <claude-code|antigravity> <pre|post> (antigravity covers App, IDE, and CLI)
# Env var PK_PROJECTS_FILE: path to JSON array of allowed origin.project slugs
#   (default: $XDG_CONFIG_HOME/personal-knowledge/projects.json, or ~/.config if XDG_CONFIG_HOME is unset)

from __future__ import annotations

import json
import os
import re
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
VOCABULARY_PATH = PLUGIN_ROOT / "vocabulary.json"
PROJECT_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*\Z")
WRITE_TOOL = re.compile(r"(?:^|basic-memory_{1,2})bm_(write|edit)$")
SERVER_NAME = re.compile(r"(?:^|_)basic-memory$")
FRONTMATTER = re.compile(r"^---[ \t]*\r?\n(.*?)\r?\n(?:---|\.\.\.)[ \t]*(?:\r?\n|$)", re.DOTALL)
KEY_VALUE = re.compile(r"""^("[^"]*"|'[^']*'|[^:]+?):(?:\s+(.*))?$""")
BLOCK_SCALAR = re.compile(r"^[|>][+-]?[0-9]*\Z")
MAX_DEPTH = 16

# ---- YAML (subset appearing in note frontmatter) ----


def _strip_inline_comment(raw: str) -> str:
    in_single = False
    in_double = False
    escaped = False
    for idx, ch in enumerate(raw):
        if escaped:
            escaped = False
            continue
        if in_double and ch == "\\":
            escaped = True
            continue
        if ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "'" and not in_double:
            in_single = not in_single
        elif ch == "#" and not in_single and not in_double:
            if idx == 0 or raw[idx - 1].isspace():
                return raw[:idx].rstrip()
    return raw


def _parse_scalar(raw: str, depth: int = 0) -> Any:
    if depth > MAX_DEPTH:
        return None
    text = _strip_inline_comment(raw).strip()
    if text in ("", "~", "null"):
        return None
    if text == "true":
        return True
    if text == "false":
        return False
    if len(text) >= 2 and text[0] == text[-1] and text[0] in ("'", '"'):
        return text[1:-1]
    if text.startswith("[") and text.endswith("]"):
        inner = text[1:-1].strip()
        return [] if inner == "" else [_parse_scalar(item, depth + 1) for item in inner.split(",")]
    if text.startswith("{") and text.endswith("}"):
        mapping = {}
        for entry in text[1:-1].split(","):
            if ":" not in entry:
                continue
            key, value = entry.split(":", 1)
            key = key.strip()
            if len(key) >= 2 and key[0] == key[-1] and key[0] in ("'", '"'):
                key = key[1:-1]
            mapping[key] = _parse_scalar(value, depth + 1)
        return mapping
    return text


def _indent_of(line: str) -> int:
    return len(line) - len(line.lstrip())


def _is_list_item(line: str) -> bool:
    body = line.lstrip()
    return body == "-" or body.startswith("- ")


def _split_key(body: str) -> tuple[str, str] | None:
    match = KEY_VALUE.match(body)
    if match is None:
        return None
    key = match.group(1).strip()
    if len(key) >= 2 and key[0] == key[-1] and key[0] in ("'", '"'):
        key = key[1:-1]
    return key, match.group(2) or ""


def _parse_block(lines: list[str], start: int, indent: int, depth: int = 0) -> tuple[Any, int]:
    if start >= len(lines):
        return None, start
    if depth > MAX_DEPTH:
        i = start
        while i < len(lines) and _indent_of(lines[i]) >= indent:
            i += 1
        return None, i
    if _is_list_item(lines[start]) and _indent_of(lines[start]) == indent:
        items: list[Any] = []
        i = start
        while i < len(lines) and _indent_of(lines[i]) == indent and _is_list_item(lines[i]):
            item_body = lines[i].lstrip()[1:].lstrip()
            kv = None if item_body == "" else _split_key(item_body)
            if kv is None:
                items.append(_parse_scalar(item_body))
                i += 1
                continue
            # "- key: value" forms a single mapping together with subsequent indented lines
            item_indent = indent + (len(lines[i].lstrip()) - len(item_body))
            rewritten = [" " * item_indent + item_body]
            j = i + 1
            while j < len(lines) and _indent_of(lines[j]) >= item_indent:
                rewritten.append(lines[j])
                j += 1
            items.append(_parse_block(rewritten, 0, item_indent, depth + 1)[0])
            i = j
        return items, i

    mapping: dict[str, Any] = {}
    i = start
    while i < len(lines) and _indent_of(lines[i]) == indent and not _is_list_item(lines[i]):
        kv = _split_key(lines[i].lstrip())
        i += 1
        if kv is None:
            continue
        key, raw_rest = kv
        rest = _strip_inline_comment(raw_rest).strip()
        if rest != "":
            if BLOCK_SCALAR.match(rest) is not None:
                mapping[key] = _parse_scalar(rest)
                while i < len(lines) and _indent_of(lines[i]) > indent:
                    i += 1
            else:
                folded = rest
                while i < len(lines) and _indent_of(lines[i]) > indent:
                    folded += " " + _strip_inline_comment(lines[i]).strip()
                    i += 1
                mapping[key] = _parse_scalar(folded)
        elif i < len(lines) and _indent_of(lines[i]) > indent:
            mapping[key], i = _parse_block(lines, i, _indent_of(lines[i]), depth + 1)
        elif i < len(lines) and _indent_of(lines[i]) == indent and _is_list_item(lines[i]):
            mapping[key], i = _parse_block(lines, i, indent, depth + 1)
        else:
            mapping[key] = None
    return mapping, i


def parse_frontmatter(content: str) -> dict[str, Any] | None:
    """Parse leading YAML frontmatter from Markdown, returning None if absent."""
    match = FRONTMATTER.match(content.lstrip("\ufeff"))
    if match is None:
        return None
    lines = [
        line
        for line in re.split(r"\r?\n", match.group(1))
        if line.strip() != "" and not line.lstrip().startswith("#")
    ]
    if not lines:
        return {}
    parsed, _ = _parse_block(lines, 0, _indent_of(lines[0]))
    return parsed if isinstance(parsed, dict) else {}


# ---- Vocabulary ----


def load_projects(env: Mapping[str, str]) -> dict[str, Any]:
    """Load the allowed origin.project slug list.

    Returns state as one of: "absent", "invalid", or "loaded".
    """
    explicit = env.get("PK_PROJECTS_FILE")
    if explicit:
        path = explicit
    else:
        xdg = env.get("XDG_CONFIG_HOME", "")
        config_home = xdg if xdg and Path(xdg).is_absolute() else str(Path.home() / ".config")
        path = str(Path(config_home) / "personal-knowledge" / "projects.json")
    try:
        text = Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        return {"state": "absent"}
    except OSError:
        return {"state": "invalid", "path": path}
    try:
        projects = json.loads(text)
    except ValueError:
        return {"state": "invalid", "path": path}
    if isinstance(projects, list) and all(isinstance(p, str) for p in projects):
        return {"state": "loaded", "path": path, "projects": projects}
    return {"state": "invalid", "path": path}


# ---- Validation ----

_ABSENT = object()


def _show(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _as_tag_list(value: Any) -> list[Any]:
    if value is _ABSENT or value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        return [tag.strip() for tag in value.split(",") if tag.strip() != ""]
    return [value]


def _check_tags(value: Any, vocabulary: dict[str, Any], violations: list[str]) -> None:
    if value is _ABSENT:
        return
    if value is not None and not isinstance(value, (str, list)):
        violations.append(f"tags must be an array of strings ({_show(value)})")
        return
    for tag in _as_tag_list(value):
        if tag not in vocabulary["tags"]:
            violations.append(f"tag {_show(tag)} is not in vocabulary")


def _check_type(value: Any, vocabulary: dict[str, Any], violations: list[str]) -> None:
    if value is _ABSENT:
        return
    if value not in vocabulary["type"]:
        violations.append(f"type {_show(value)} is not in vocabulary")


def _check_origin(value: Any, vocabulary: dict[str, Any], projects: dict[str, Any], violations: list[str]) -> None:
    if value is _ABSENT:
        return
    if not isinstance(value, dict):
        violations.append(f"origin must be an object with kind and project ({_show(value)})")
        return
    if "kind" in value and value["kind"] not in vocabulary["originKind"]:
        violations.append(f"origin.kind {_show(value['kind'])} is not in vocabulary")
    project = value.get("project")
    if project is None:
        return
    if not isinstance(project, str) or PROJECT_SLUG.match(project) is None:
        violations.append(f"origin.project {_show(project)} is neither a slug (lowercase letters, digits, hyphens) nor null")
        return
    if projects["state"] == "invalid":
        violations.append(f"origin.project list ({projects['path']}) cannot be read as a JSON array of strings")
    elif projects["state"] == "loaded" and project not in projects["projects"]:
        violations.append(f"origin.project {_show(project)} is not in the environment list ({projects['path']})")


def _check_status(value: Any, note_type: Any, vocabulary: dict[str, Any], violations: list[str]) -> None:
    if value is _ABSENT or value is None:
        return
    if isinstance(note_type, str):
        allowed = vocabulary["status"].get(note_type)
    else:
        allowed = [s for values in vocabulary["status"].values() for s in values]
    if allowed is None:
        violations.append(f"notes of type {_show(note_type)} must not have status")
    elif value not in allowed:
        shown_type = note_type if isinstance(note_type, str) else "unknown"
        violations.append(f"status {_show(value)} is not in vocabulary for type {_show(shown_type)}")


def _check_fields(
    source: dict[str, Any] | None,
    note_type: Any,
    vocabulary: dict[str, Any],
    projects: dict[str, Any],
    violations: list[str],
) -> None:
    if not isinstance(source, dict):
        return
    _check_type(source.get("type", _ABSENT), vocabulary, violations)
    _check_tags(source.get("tags", _ABSENT), vocabulary, violations)
    _check_origin(source.get("origin", _ABSENT), vocabulary, projects, violations)
    _check_status(source.get("status", _ABSENT), note_type, vocabulary, violations)


def _check_required(note: dict[str, Any], vocabulary: dict[str, Any], violations: list[str]) -> None:
    if not _as_tag_list(note.get("tags")):
        violations.append("tags is required")
    origin = note.get("origin")
    if origin is None:
        violations.append("origin is required")
    elif isinstance(origin, dict):
        if "kind" not in origin:
            violations.append("origin.kind is required")
        if "project" not in origin:
            violations.append("origin.project is required (use null if not derived from a specific project)")
    note_type = note.get("type")
    if isinstance(note_type, str) and note_type in vocabulary["status"] and note.get("status") is None:
        violations.append(f"notes of type {_show(note_type)} require status")


def find_violations(
    tool: str,
    args: dict[str, Any],
    vocabulary: dict[str, Any],
    projects: dict[str, Any],
) -> list[str]:
    """Return closed-vocabulary violations for a write/edit tool call's frontmatter.

    `tool` must be "write" or "edit". Returns an empty list if valid.
    """
    violations: list[str] = []
    metadata = args.get("metadata")
    if not isinstance(metadata, dict):
        metadata = None

    if tool == "edit":
        _check_fields(metadata, (metadata or {}).get("type", _ABSENT), vocabulary, projects, violations)
        return violations

    content = args.get("content")
    frontmatter = parse_frontmatter(content if isinstance(content, str) else "") or {}
    # Because precedence between parameters and inline frontmatter depends on the server,
    # validate each source individually and check required fields on the merged view.
    param_type = args.get("note_type") if isinstance(args.get("note_type"), str) else "note"
    param_tags = args.get("tags", _ABSENT)
    if param_tags is None:
        param_tags = _ABSENT
    note: dict[str, Any] = {"type": param_type}
    if param_tags is not _ABSENT:
        note["tags"] = param_tags
    note.update(frontmatter)
    note.update(metadata or {})
    if not _as_tag_list(note.get("tags")) and param_tags is not _ABSENT:
        note["tags"] = param_tags
    note_type = frontmatter.get("type", (metadata or {}).get("type", param_type))
    note["type"] = note_type

    _check_fields(frontmatter, note_type, vocabulary, projects, violations)
    _check_fields(metadata, note_type, vocabulary, projects, violations)
    type_given = "type" in frontmatter or "type" in (metadata or {})
    from_params: dict[str, Any] = {} if type_given else {"type": param_type}
    if param_tags is not _ABSENT:
        from_params["tags"] = param_tags
    _check_fields(from_params, note_type, vocabulary, projects, violations)
    _check_required(note, vocabulary, violations)
    return list(dict.fromkeys(violations))


def write_tool_kind(tool_name: Any) -> str | None:
    """Return "write" or "edit" if tool_name targets a knowledge-base write tool, else None."""
    if not isinstance(tool_name, str):
        return None
    match = WRITE_TOOL.search(tool_name)
    return None if match is None else match.group(1)


def _deny_reason(violations: list[str]) -> str:
    return (
        "Blocked knowledge-base write because frontmatter violates the closed vocabulary:\n"
        + "\n".join(f"- {v}" for v in violations)
        + "\nThe canonical vocabulary is vocabulary.json in the plugin. Rewrite using allowed values. "
        + "If a new value is needed, propose adding it to the user instead of writing. "
        + "Allowed origin.project values are configured per environment."
    )


def _verify_context(args: dict[str, Any]) -> str:
    project = json.dumps(args["project"]) if isinstance(args.get("project"), str) else '"<target-project>"'
    if isinstance(args.get("identifier"), str):
        target = f'identifier={json.dumps(args["identifier"])}'
    elif isinstance(args.get("title"), str):
        target = f'identifier={json.dumps(args["title"])}'
    else:
        target = "the written note's identifier"
    return (
        "Knowledge-base write succeeded. Frontmatter was checked before writing, "
        "but observation categories and relation schemas have not been verified yet. "
        f"Verify with bm_schema(command=\"validate\", project={project}, {target})."
    )


def _read_stdin() -> Any:
    try:
        return json.loads(sys.stdin.buffer.read().decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None


def _write_stdout(output: dict[str, Any]) -> None:
    sys.stdout.buffer.write(json.dumps(output, ensure_ascii=False).encode("utf-8"))
    sys.stdout.buffer.flush()


def main(argv: list[str]) -> None:
    product = argv[1] if len(argv) > 1 else None
    phase = argv[2] if len(argv) > 2 else None
    data = _read_stdin()
    if not isinstance(data, dict):
        return

    if product == "claude-code":
        tool_name = data.get("tool_name")
        args = data.get("tool_input")
    elif product == "antigravity":
        call = data.get("toolCall")
        if not isinstance(call, dict):
            return
        call_args = call.get("args") if isinstance(call.get("args"), dict) else {}
        if call.get("name") == "call_mcp_tool":
            # In default lazy-loaded MCP configs, generic call_mcp_tool wraps ServerName/ToolName
            server = call_args.get("ServerName")
            if not isinstance(server, str) or SERVER_NAME.search(server) is None:
                return
            tool_name = call_args.get("ToolName")
            args = call_args.get("Arguments")
        else:
            tool_name = call.get("name")
            args = call_args
    else:
        return
    kind = write_tool_kind(tool_name)
    if kind is None or not isinstance(args, dict):
        return

    if phase == "pre":
        vocabulary = json.loads(VOCABULARY_PATH.read_text(encoding="utf-8"))
        violations = find_violations(kind, args, vocabulary, load_projects(os.environ))
        if not violations:
            return
        if product == "claude-code":
            _write_stdout(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": _deny_reason(violations),
                    }
                }
            )
        else:
            _write_stdout({"decision": "deny", "reason": _deny_reason(violations)})
    elif phase == "post" and product == "claude-code":
        # Antigravity PostToolUse does not support returning additionalContext to the agent
        _write_stdout({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": _verify_context(args)}})


if __name__ == "__main__":
    try:
        main(sys.argv)
    except Exception:
        # Fail open on unexpected errors
        pass
