# Requirements and authority

Open when establishing the scope or recovering a skill-authoring task.

Read the owner's current request and settled decisions before choosing a workflow.
Reuse answered questions. Ask only for missing information that changes the result.
Do not silently expand scope, invent approval gates or treat a generated plan as authority.

Capture requirements once in the explicit work directory. Include the skill's purpose,
users, activation boundaries, source/version limits, licensing, accepted conventions,
excluded paths, allowed mutations and the owner-review gate.
Keep a separate mutable checkpoint; see [continuity](../operations/continuity.md).

The public [Agent Skills specification](https://agentskills.io/specification) defines
the portable frontmatter and resource layout. It does not mandate this library's
three headings, 100 physical lines, topics.json, four folders or review workflow.
Those are the selected authoring profile here. Do not present them as universal rules.

The owner may change this profile explicitly. Record the change before adapting tooling;
do not loosen checks merely because an output fails them.
No generated requirements file or checksum outranks a later explicit owner decision.

Define success in observable terms: activation, correct reference selection, useful task
completion, intact source contracts, readable names and safe publication.
List verification obligations before authoring. A plan is ready only after its atomic
file tasks and their checks exist. Add needed repair tasks before applying those edits.

Match verification to the work: inspect rendered artifacts for a document-producing skill;
exercise state transitions and failure recovery for an automation skill; verify real or
recorded tool contracts for an MCP workflow. Tools must actually be available and authorized.
Do not combine unrelated jobs just because they share an authoring tool.

Never use this skill's obsolete output, model memory or an engine template to override
the owner's instructions. Keep skill-building guidance inside authoring skills only.
