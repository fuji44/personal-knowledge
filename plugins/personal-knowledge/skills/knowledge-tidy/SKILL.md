---
name: knowledge-tidy
description: Audit and tidy the entire knowledge base: review confidence levels, verify promotion targets exist, fix schema discrepancies, repair broken links, and maintain index notes. Use when asked to tidy or audit the knowledge base, or when search results conflict with reality. Does not cover in-session capture, distilling logs, or auditing built-in agent memory.
---

# Tidy Knowledge Base

The goal is accuracy. Stale notes cause agents to assert falsehoods instead of checking reality. Proceed with non-lossy fixes; leave merges, deletions, and contradiction resolutions as proposals. Note authoring conventions from the `personal-knowledge` skill apply.

## Steps

1. **Validate schemas.** Run `bm_schema(command="validate")` and fix discrepancies. Inspect per-type drift trends with `command="diff"`.
2. **Check links.** Find unresolved `relation` targets and either create the missing target note or fix the relation.
3. **Review confidence.** List `tentative` notes: upgrade to `established` when supporting logs have grown, or revise/mark notes disproven by counterevidence. Update `last_verified` on `entity` and `concept` notes only when checked against actual behavior or source code.
4. **Verify promotion targets.** Check that every `adopted` `practice` note's `promoted_to` repository, path, and heading still exist (headings silently break when edited). Notify the user if a norm was removed from its promotion target.
5. **Check norm placement.** Propose promotion for `candidate` `practice` notes whose supporting records now meet promotion criteria.
6. **Update indexes.** Create a tag index note whenever 5 or more distilled knowledge (`entity`, `concept`, `decision`) and `practice` notes share a tag, and link it from the root index.
7. **Record a reflection.** Write what was audited, fixed, and proposed in a `reflection` note.

## Done Criteria

Show before/after counts (total notes, schema discrepancies, broken links, `tentative` notes) along with a list of fixes applied and changes proposed.
