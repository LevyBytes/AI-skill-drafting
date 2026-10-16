# Activation and task evaluations

Open when measuring whether the skill is selected and helps complete real work.

Use [activation cases](../../evals/activation-cases.json) for direct requests, paraphrases,
near misses and unrelated requests. Judge the intended skill, first reference and outcome.
Do not score a keyword match as model activation. Run cases in fresh contexts with the
same discovery metadata the target client sees, and preserve model/version and transcripts.

Use [task cases](../../evals/evals.json) for a new package, a damaged example repair and
a multi-product package. Follow the [run instructions](../../evals/EVALS.md) and
[grading criteria](../../evals/grading.md).
The assistant should select relevant guidance, propose coherent content, preserve source
contracts, prepare all tasks, stage only, report limits and respect review before deployment.
Test a resumed task with a changed input hash and an apparent approval for another digest.

Score activation, route selection, task correctness, unnecessary reads, unauthorized
mutations and evidence quality separately. Compare to a no-skill baseline where practical.
Manual review must assess names and organization; counts cannot replace that judgment.

When independent agent review is explicitly authorized and available, provide the raw
artifact and realistic task without leaking the expected answer. Give each reviewer a
bounded scope and inspect every returned change. Otherwise use separate self-review
passes and say so; tool availability alone does not authorize delegation.

The deterministic suite validates fixture structure and actual CLI behavior. It does not
call an external model or claim activation quality. Record model-based evaluation as
not run until genuine harness runs and reviewer scores are available.
Use [the evaluation record](../../assets/evaluation-record.json) to capture those results.

Update triggers from observed false positives/negatives, keeping descriptions concise.
Do not broaden a skill to unrelated domains merely to increase activation.
