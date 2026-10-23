# Regression and behavior checks

Open when proving the authoring tools prevent a known defect.

Run `scripts/tests/run.py --work <new-disjoint-test-directory>` with the selected interpreter.
Tests leave inspectable artifacts outside the skill. Set PYTHONDONTWRITEBYTECODE=1 to
avoid caches in the installed package. Review test code before running it.

Pair each real defect with a failing input, repaired output and meaningful assertion:

- Flattened comments: lost newlines hide imports/calls; retain a reviewed repaired example.
- Nested collections: organize first, then reject repeated ancestors and nested references.
- Ancestor repetition: reject singular/plural repetition such as
  `references/reference` and `handlers/handler`, including separated or empty folders.
  Preserve distinct qualifiers and exact API identifiers; reject before rendering or
  snapshot creation. Include negative controls for words such as `status` and `news`.
- Shared names: distinguish implementation excerpts from API contracts with the same names.
- Dynamic properties: strict property mocks catch wrong settings; preserve valid defaults.
- Source fidelity: preserve preambles, API ownership, complete declarations and
  tables; catch hidden literals, malformed fences and missing HTML image targets.
- Common: 99/100/101 lines, collisions, missing translations, malformed catalogs,
  frozen-artifact drift, wrong approval, interruption/resume and safe rollback.
- Long paths: reject page titles captured whole as names; accept reviewed short destinations.
  Exercise name lengths 63/64/65, relative paths 159/160/161, single depths 3/4/5,
  collection depths 5/6/7, missing or false collection declarations,
  Unicode code points, binary and empty-directory paths, and product-root prefixes.
  A target overrun alone must pass; hard overruns must block rendering and preparation.
  A malformed nested skill must not grant the collection depth allowance.

Behavior examples must exercise an actual result, not merely duplicate implementation.
A syntax check cannot detect assigning a nonexistent dynamic property or wrong API owner.
A mock proves only the modeled contract; a native application test proves a different scope.
Use adversarial inputs and positive controls to avoid overzealous “repairs”.

The software suite in scripts/tests uses disposable new, repaired and multi-product skills.
Agent-use tasks and their inputs live separately in evals; their scores require actual runs.
A large generated inventory exercises path checks at collection scale.

Record interpreter/dependency versions, passed/failed/not-run checks and exact outputs.
Do not execute arbitrary code from a proposal as part of verify. Explicitly review and
run bounded behavior fixtures in a separate disposable environment.
