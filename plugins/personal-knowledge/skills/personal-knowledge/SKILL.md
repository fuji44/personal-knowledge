---
name: personal-knowledge
description: How to use and author notes in the personal knowledge base (basic-memory MCP). Covers project selection, tool usage, note classification, granularity, revision, confidence/promotion, and exclusions. Use when searching or reading the knowledge base, writing or editing notes, or asked to search past findings or save a note. Does not cover the capture, distill, or tidy workflows themselves.
---

# Personal Knowledge (`basic-memory`) Skill

Procedures for reading and writing the Markdown-based knowledge graph through the `basic-memory` MCP server (default `http://localhost:48000/mcp`).

## 1. Confirm and Select the Project (Required)

`basic-memory` isolates projects by context—such as personal hobby projects and individual client or work engagements.

1. If the target project is not yet confirmed, call `bm_project` (`command: "list"`) first to list available projects.
2. Identify the `project` name matching the current workspace or conversation context.
   - Choose the target based on content, not the machine you are connecting from. Broadly applicable knowledge (including work learnings stripped of proper nouns, internal identifiers, and confidential data) goes into a general-purpose project; engagement-specific information goes into that engagement's project. From a work machine, do not access other engagements or private personal projects unless explicitly instructed.
   - If a new project is needed or the destination is ambiguous, confirm with the user before running `bm_project(command="create", name="...", path="...")`.

## 2. Tool Usage

Always pass the **`project` parameter explicitly** on every note operation.

| Goal | Tool | Usage |
| --- | --- | --- |
| List projects / recent updates | `bm_project` | `command: "list"` to list projects; `command: "recent"` to inspect recent changes |
| List notes in a folder | `bm_list` | Specify `path: "/"` (root) or a subdirectory |
| Search by filename / frontmatter | `bm_find` | Filter with `name: "*.md"` or `filters` |
| Full-text / semantic search | `bm_search` | Pass `query` and `project` to find related notes |
| Read a note | `bm_read` | Pass `identifier` (path, title, or `memory://` URL) and `project` |
| Retrieve graph context | `bm_context` | Traverse relations from a note to load connected notes |
| Create or overwrite a note | `bm_write` | Save with title, folder, body, and tags |
| Partially edit an existing note | `bm_edit` | Safely update via `append`, `prepend`, `find_replace`, `replace_section`, etc. |

## 3. Authoring Rules

Definitions for `type`, observation categories, `relation`, `status`, and `tags`, along with per-type schemas, live inside the knowledge base itself (follow links from the root index note; schemas are notes with `type: schema`). The single source of truth for closed frontmatter vocabulary (`type`, `tags`, `status`, `origin.kind`) is `vocabulary.json` in this plugin. The allowed `origin.project` slugs are configured per environment. Read the definitions before writing, and verify with `bm_schema(command="validate")` afterward. A pre-write hook validates frontmatter and blocks writes outside the closed vocabulary.

### Classification

- Assign `type` by checking definitions in order: `schema`, `index`, `reflection`, `log`, `source`, `decision`, `practice`, `entity`, `concept`—use the first match.
- Decide `entity` vs. `concept` at the note level: if the content still holds when you swap out the specific tool, it is a `concept`. Split tool-specific lines into an `entity`.
- Write normative statements (`rule` / `exception`) only in `practice` notes. Keep `practice` bodies limited to `rule` / `exception` / `rationale` / `technique`; place tool facts and pitfalls in `entity` notes and link them with `depends_on`.
- Write `event` / `finding` / `feedback` only in raw `log` notes. Record `feedback` verbatim and record your response as an `event`.
- Write `context` / `decision` / `rejected` / `consequence` only in `decision` notes.
- Author `relation` in one direction only; reverse links are traversed via backlinks.

### Granularity

- One topic per note. One observation covers a single fact or rule together with its condition, rationale, and concrete example.
- Do not record history, counts, or incidents inside `concept` / `entity` / `practice` notes; write them in `log` notes and link via `derived_from`. Keep one `log` per incident so supporting evidence remains countable.
- Do not delete superseded facts; close their validity window with `@effective[start,end)`.
- Decide whether to keep a line by asking: "Would removing this line change the AI's next action?"
- Keep the note title and `# Heading` identical. Links resolve by title, so do not use permalinks as human-readable names.

### Revision

- Raw notes (`log` and `source`) are append-only. When a `question` is answered, append the answer on a new line.
- Evolve `concept` and `entity` notes in place. Never rewrite a `decision` body; write a new `decision` with `supersedes` and update only the old decision's `status` to `superseded`.
- Update `last_verified` only when you have verified the note against actual behavior or source code.

### Confidence and Promotion

- On the first AI-observed lesson, write a `log`, and if normative, write a `practice` with `status: candidate`.
- Propose promotion to instructions or skills on the 2nd occurrence, and to a hook or lint check on the 3rd occurrence (or immediately if mechanically checkable from the start). For conventions decided by a human, propose promotion on the 1st occurrence. Humans approve promotions.
- Once promoted, set `status` to `adopted`, add the target to `promoted_to` (`kind`, `repo`, `path`, `anchor`), add its `kind` to `promoted_kinds`, and remove the `rule` and `exception` lines from the note (keeping `rationale` and `technique`). Promotion targets must live in version-controlled repositories.

### What Not to Write

- Environment-specific values (local paths, hostnames, environment variables, machine-local settings). Reference files using repository-relative identifiers.
- Company proper nouns, internal identifiers, business data, or confidential information—including combinations of domain terms that reveal internal architecture. Generalize work learnings by removing these details; the only exception is `origin.project` in frontmatter, which holds a slug naming the review/confidentiality boundary.
- Full session transcripts.

### Indexing

- The root index note links only to topic index notes.
- When 5 or more distilled knowledge notes (`entity`, `concept`, `decision`) and `practice` notes share a tag, create a tag index note and link it from the root index. Do not count raw (`log`, `source`) or `reflection` notes.
- Frontmatter `tags` use a closed vocabulary. When a new tag is needed, propose adding it to `vocabulary.json` to the user before writing.
