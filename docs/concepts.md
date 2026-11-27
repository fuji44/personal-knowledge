# Concepts & References

## Knowledge Lifecycle

Rather than keeping a single flat folder of notes, `personal-knowledge` organizes knowledge by maturity so transient observations do not masquerade as verified rules:

1. **Capture (`log`)**: Append-only incident records written during a session when tools behave unexpectedly, assumptions are disproven, or decisions are made.
2. **Distill (`entity`, `concept`, `decision`, `practice`)**: Evergreen notes derived from logs via `derived_from`. Tool-specific facts live in `entity` notes, tool-independent principles in `concept` notes, choices in immutable `decision` notes, and normative guidance in `practice` notes.
3. **Promote**: Once a `practice` recurs or is adopted as a human convention, its rules move into version-controlled instructions, skills, or automated hooks/lints, leaving rationale and techniques in the knowledge base.
4. **Tidy (`reflection`)**: Periodic audits run `bm_schema` validation, repair broken relations, review confidence levels against supporting logs, and verify that promotion targets still exist.

For exact closed-vocabulary values and per-workflow rules, treat [vocabulary.json](../plugins/personal-knowledge/vocabulary.json) and the skill definitions under [plugins/personal-knowledge/skills/](../plugins/personal-knowledge/skills/) as the single source of truth.

## Scope Separation

Projects in `basic-memory` isolate contexts (e.g., general-purpose engineering knowledge vs. individual work engagements), routed by **content rather than client machine**:

- Broadly applicable lessons—including work learnings stripped of proper nouns, internal identifiers, and confidential data—belong in a general-purpose project.
- Engagement-specific details stay in that engagement's project and are never read or written outside explicit user direction.
- Frontmatter `origin.project` records provenance as a slug so review and confidentiality boundaries remain auditable.

See [plugins/personal-knowledge/rules/AGENTS.md](../plugins/personal-knowledge/rules/AGENTS.md) for the enforced rules.

## Tools & References

### Core Tools

- [Basic Memory](https://github.com/basicmachines-co/basic-memory) — Markdown-based knowledge graph exposed via MCP.
- [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) — Standard protocol for connecting AI clients to external tools and context.

### Concepts & Further Reading

- **Zettelkasten & Evergreen Notes** — Atomic, concept-oriented notes linked together rather than siloed by folder ([Andy Matuschak's Evergreen Notes](https://notes.andymatuschak.org/Evergreen_notes)).
- **Architecture Decision Records (ADRs)** — Immutable decision records with explicit supersession rather than silent edits ([Michael Nygard, *Documenting Architecture Decisions*](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)).
