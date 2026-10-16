# Deployment and recovery

Open when applying an accepted candidate, resuming an interruption or restoring a deployment.

Review the complete candidate, decisions, tasks, diffs, structural report and behavior
evidence. Do not deploy merely because verification passed. Record the actual owner's
authorization and the exact candidate digest returned by apply.

```powershell
& $Python $Builder deploy --work $Work --destination $Input --approved-digest $Digest --authorization 'Owner approved this exact candidate.'
& $Python $Builder rollback --work $Work --authorization 'Owner approved restoring the captured input.'
```

An authorization string records a caller decision; it cannot authenticate a human.
Do not invent it. Deployment must target the captured input root. It checks live drift,
candidate hashes and verification, preserves Git, snapshots rollback, then journals each
file outcome. It never runs git add, commit or push.

Resume the same command after a handled interruption. Every current file must equal its
recorded before or after bytes; any unexplained third state refuses continuation.
After completion, an altered candidate or deployment is rejected, not overwritten.
Rollback likewise refuses intervening edits and resumes only its recorded transaction.
Create a new preparation after rollback or when making a new revision.

A process crash may leave `transaction.lock` or a `.writing` file. The tool deliberately
refuses these rather than guessing whether another writer is active or data is disposable.
Confirm the writer is stopped; preserve the work directory; inspect the pending file
against before/after hashes; resolve that specific artifact before resuming.
Do not recursively delete a work tree or clear all locks by pattern.
File-to-directory and directory-to-file replacements are refused before file mutations.
Prepare a separate reviewed revision when such a structural conversion is needed.
Per-file outcomes are append-only JSONL in the work directory. An incomplete final record
also requires inspection; do not discard an outcome merely to make a resume succeed.

Prepared snapshots, requirements, decisions, evidence and diffs are hash-checked on resume.
Hashes detect drift, not malicious tampering by someone able to replace the whole work tree.
Keep that directory trusted. Avoid concurrent editors during mutation: the lock excludes
this tool's writers, not arbitrary editors. Filesystem operations are not a database transaction.

If a new problem needs a repair, prepare a new revision with atomic tasks before editing
the candidate. Preserve the reviewed predecessor and do not replay an old preparation.
