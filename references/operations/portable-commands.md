# Portable commands

Open when using the bundled builder on a new or repaired skill.

Use an explicitly chosen Python 3.12+ interpreter. Install the dependencies declared in
`scripts/requirements.txt` into that environment if missing. Do not change a shared
interpreter, PATH or environment without authorization. No Kaizen runtime is required.

The examples below use `$Python` for an absolute interpreter path and `$Builder` for
the absolute `scripts/skill_builder.py` path. Set all other paths explicitly.

```powershell
& $Python $Builder inspect --input $Input
& $Python $Builder render --spec $Spec --output $Proposal
& $Python $Builder verify --input $Proposal
& $Python $Builder prepare --input $Input --proposal $Proposal --work $Work --requirements $Requirements --decisions $Decisions --evidence $Evidence
& $Python $Builder status --work $Work
& $Python $Builder apply --work $Work
```

Input is an existing directory, empty for a fresh skill. Proposal and work must be
disjoint from input and each other. render output and prepare work must not exist.
The proposal's main folder name must match its frontmatter for standalone verify.
apply creates `work/candidate/<skill-name>` and stops at awaiting_owner_review.
For recognized products, verify accepts `--roots . product-one product-two`.
The collection root must also declare string metadata `skill-type: collection`.
The `--roots` option controls scaffold ownership; it does not grant extra depth.
Valid nested entrypoints and the metadata declaration together select six levels;
a single skill has a four-level hard limit.

Exit status: zero for success, one for verification findings, two for refusal/input error.
Commands print JSON. They do not execute snippets, access a provider, fetch the web,
infer workspace paths or publish Git. Read command help for exact arguments.

Use [the render example](../../assets/render-example.json) as the smallest complete input.
Its [schema](../../assets/render-schema.json) is enforced before output is written.
The [decisions example](../../assets/decisions-example.json) accounts for every output
of that fresh package; the [decision schema](../../assets/decisions-schema.json) documents
preserve, rewrite and exclusion records. Adapt it to the actual reviewed input.
For large hand-authored proposals, prepare accepts a complete folder directly; render is
optional. Every route, source decision and complete file must still be prepared.

See [deployment and recovery](deployment-and-recovery.md) before mutating a live root.
