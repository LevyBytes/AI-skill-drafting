# Source maps and preservation

Open when preparing a proposal that changes, splits, merges or removes source files.

Every input file has one disposition: preserve, rewrite or exclude. Preserve requires
one byte-identical output; it can rename that output. Exclude has no output and needs a
specific reason. Rewrite lists all resulting files, a reason and reviewed source ranges.
Ranges must cover every physical source line exactly once, including the preamble.

Every output must be mapped from a source or explicitly justified as created.
The generated manifest separately records every changed/created/removed path as one
atomic task with before/after hashes and a diff. Unchanged files remain in inventories.
One task belongs to this owning preparation; tasks are not discovered after application.

For code=preserve, connected rewrite mappings compare the multiset of protected code
blocks before and after. This allows a block to move between coherently split files.
Raw source files are protected as complete text. Added or removed blocks fail comparison.
For code=repair, list captured evidence paths and the exact behavior-check result or
honest not-run rationale. The tool does not infer that an asserted test passed.

Range coverage proves the declaration covers the source, not that a paraphrase preserves
meaning. Review output against source, including identifiers, API ownership, tables and
prerequisites. Explain deletions; do not treat an exclude disposition as automatic approval.

Binary rewrites are not supported by the rewrite checker. Preserve exact binaries or
record an explicitly reviewed exclusion plus independently supplied replacement.
Preserve the skill's own LICENSE and NOTICE exactly unless the owner separately authorizes a license change.
This tool profile refuses changes to existing LICENSE, LICENCE, COPYING and NOTICE
files, including moves. A separately authorized license change needs its own reviewed flow.

Keep requirements, source evidence, decisions, source maps, snapshots and rollback in
the work directory. Do not ship the whole repair history inside a product skill.
