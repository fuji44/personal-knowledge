# Personal Knowledge (`basic-memory`) Rules

When using the personal knowledge base (`basic-memory` MCP server), strictly follow the scope separation rules below.

## Project Selection and Isolation Principles

1. **Always specify `project` explicitly:**
   - When calling `basic-memory` tools (`bm_write`, `bm_edit`, `bm_read`, `bm_search`, `bm_find`, `bm_list`, `bm_context`, etc.), always pass the **`project` parameter** corresponding to the current task context.
   - If the available projects are unknown, check them first with `bm_project(command="list")`.
   - If the target project is ambiguous, confirm with the user before writing.
2. **Route by content, not by client machine:**
   - Knowledge that applies broadly across projects—including lessons learned at work once generalized by stripping proper nouns, internal identifiers, and confidential details—may be read and written in a general-purpose project from any machine. Record the origin only as a slug in frontmatter (`origin.project`) to define the boundary for review and confidentiality. Learning from work is normal and should not be treated as an exception.
   - Information specific to a particular company or engagement belongs in that engagement's project. From a work machine, never read, search, or write to other clients' projects or private personal projects unless explicitly instructed by the user.
   - Never write confidential business data or proprietary code outside its target engagement's project. If you are unsure whether something can be fully generalized, do not write it to the general-purpose project.

## Authoring Notes

Before writing or editing notes, read the `personal-knowledge` skill for usage and authoring rules. Separate skills cover capturing logs (`knowledge-capture`), distilling logs into evergreen knowledge (`knowledge-distill`), and tidying the knowledge base (`knowledge-tidy`).
