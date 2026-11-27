---
name: knowledge-distill
description: Distill accumulated event logs in the knowledge base into tool knowledge (entity), general principles (concept), norms (practice), and decisions (decision). Use when asked to distill, organize logs, summarize into knowledge, or migrate built-in agent memory into the knowledge base. Does not cover in-session capture or full knowledge-base tidying.
---

# Distill Knowledge

Distillation is triggered by the user. Proceed autonomously with non-lossy edits (splitting notes, aggregating with source attribution); leave merges, deletions, and conflict resolution as proposals awaiting human judgment. Note authoring conventions from the `personal-knowledge` skill apply.

## Steps

1. **Select scope.** Unless the user specifies a range, list all `log` notes not yet referenced via `derived_from` by any distilled knowledge (`entity`, `concept`, `decision`) or `practice` note.
2. **Classify note types.** Separate log contents into facts/pitfalls (`entity` or `concept`), norms (`practice`), and choices (`decision`), applying the type rules in order.
3. **Search existing notes.** If a note already exists for the same tool, principle, or norm, update it rather than creating duplicates with slightly different wording.
4. **Author distilled notes.** Omit incident history, counts, and anecdotes from `entity`, `concept`, and `practice` notes—point back to `log` notes with `derived_from`. Set confidence based on supporting logs (`established` requires 2+ independent logs, intentional reproduction, or recorded human confirmation).
5. **Propose promotions.** For `practice` notes representing human conventions or observed 2+ times, propose a promotion target (always-on instructions, skill/runbook, or automated hook/lint).
6. **Handle migration sources.** When migrating from built-in agent memory, verify the written notes first, then propose deleting the source entries. Do not delete the source of a norm that has not yet been promoted.
7. **Validate.** Confirm all `relation` targets resolve and schema validation passes.

## Done Criteria

Present a summary list of created/updated notes, proposed promotions, and proposed merges or deletions. For any target `log` skipped without distillation, explain why.
