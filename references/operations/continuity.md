# Continuity across long sessions

Open when starting, resuming, compacting or handing off a skill-authoring task.

Keep stable requirements and mutable progress separate. prepare snapshots REQUIREMENTS.md
and binds its digest in manifest.json. status checks that snapshot plus decisions, input,
proposal, evidence and diffs. checkpoint.json records the current review/deployment state.

Before continuing after compaction or handoff:

1. Read the frozen requirements in full and verify their hash through status.
2. Read the latest owner directions, exclusions, approvals and checkpoint.
3. Inspect the exact active candidate, prepared manifest and per-file outcomes.
4. Investigate unexplained changed hashes before overwriting anything.
5. Continue only the next authorized action; stop at the owner-review gate.

Do not replace requirements with a summary or silently edit them to match implementation.
Later owner directions can authorize a new revision; preserve the earlier record.
Do not describe a prepared plan as ready until all its atomic tasks and checks exist.

Use [the working-brief template](../../assets/work-brief.md.template) for human notes.
Include absolute artifact paths where a handoff needs them, source provenance, test scope,
known unresolved findings and the next action. Keep session paths out of portable skills.

A file is a reread obligation, not a compaction event hook. Do not claim automatic reload,
modify agent configuration or write persistent memory without explicit authorization.
