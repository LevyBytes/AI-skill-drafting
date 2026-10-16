# Skill-use evaluations

These cases measure how an agent uses this skill to complete realistic authoring work.
They are separate from the software tests in scripts/tests.

Use [evals.json](evals.json) for three task cases and their supplied inputs, expected
outcomes and assertions. Use [activation cases](activation-cases.json) separately for
discovery and first-reference selection. Read [grading criteria](grading.md) before scoring.

Run each task in a fresh authorized session with the skill, then without it or with a
preserved earlier version. Give the agent only the selected prompt, its supplied input
files, the skill path when applicable, and an explicit disposable output directory.
Keep expected outcomes, grading criteria and prior scores with the evaluator rather
than coaching the agent toward a known answer. Do not automatically spawn agents or
call a provider; follow the current owner's authorization and runtime capabilities.

Put outputs, transcripts, timing and grading beside the skill in a separate work folder,
organized by iteration, case and with-skill/baseline configuration. Preserve input hashes.
Record model/client versions and actual measured time/tokens; leave unavailable values
unknown. Do not manufacture timing, evaluation scores or baseline results.

The case definitions have been checked for consistency. Agent runs and comparative
quality scores remain not run until real isolated executions are performed.

This follows the [Agent Skills evaluation guidance](https://agentskills.io/skill-creation/evaluating-skills).
