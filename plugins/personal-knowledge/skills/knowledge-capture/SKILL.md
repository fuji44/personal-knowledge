---
name: knowledge-capture
description: Record learnings, pitfalls, decisions, and human feedback obtained during a session as event logs in the knowledge base. Use when a tool behaves unexpectedly, when corrected by a user, when a user states a policy, when choosing among options, when an assumption is disproven, or when about to write to built-in agent memory. Does not cover distilling logs into structured knowledge or tidying the knowledge base.
---

# Capture Knowledge

Capture events during a conversation at the AI's discretion. Distilling logs into structured understanding happens when the user triggers it, so focus here on preserving raw events accurately. Note authoring conventions from the `personal-knowledge` skill apply.

## What to Capture

Record when any of the following occurs (when in doubt, capture):

- A tool, library, or API behaved differently than assumed
- A user corrected you or stated a policy/convention
- A choice was made among alternatives (with rejected options and rationale)
- Testing or investigation disproved an existing assumption or note

Decide placement first: broadly applicable learnings go to the knowledge base regardless of confidence; environment-specific or engagement-specific facts—and lessons you are unsure how to generalize—go to the agent's built-in memory. Split them if a lesson contains both.

## Steps

1. **Search existing logs.** If a `log` already exists for the same event, append to it. If a related knowledge (`entity`, `concept`, `decision`) or `practice` note exists, inform the user after recording.
2. **Write one `log` per incident.** Title it as a short sentence describing the event without a date:
   - `[event]` What happened (include the date in the body if known)
   - `[finding]` What was discovered
   - `[feedback]` Verbatim user feedback (redact proprietary company terms)
3. **Generalize.** Strip company proper nouns, internal identifiers, and business data. If stripping them breaks meaning, keep that part on the engagement side. Record provenance in frontmatter `origin` (`kind` and `project`).
4. **If a norm is present, draft a `practice` with `status: candidate`.** Propose promotion immediately for human-decided conventions; for AI-observed lessons, propose promotion on the 2nd occurrence.
5. **Review after writing.** Check that title and `# Heading` match, relations resolve, and schema validation passes.

## Done Criteria

Report the title(s) of written notes and any proposed promotions (one per line) to the user.
