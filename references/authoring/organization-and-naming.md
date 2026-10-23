# Organization and naming

Open when grouping source material, choosing paths or repairing misleading names.

Inspect actual content across the whole root before grouping it. Source navigation,
download buckets, filenames and matching prefixes are evidence, not the final taxonomy.
Group content by context type, using its actual subject, API ownership and workflow.
Order groups and their routes by the task and its dependencies, never alphabetically.
Do not use first-letter buckets, lexical ranges or arbitrary entry counts as categories.
For example, group a product's references into setup, everyday tasks, automation and
troubleshooting workflows, not A-C or names beginning with a letter.
Keep guide and API material discoverable together while distinguishing their purpose.
Preserve exact API owners, case, versions, signatures, parameters and return contracts.

Classify an API by its own behavior and definition. Shared inherited properties and
boilerplate do not determine its subject: a date-formatting helper belongs with
text formatting, not database access merely because both expose the same base methods.
Review ambiguous assignments individually. Repair discovered context defects and
check related routes for the same mistake before accepting the staged skill.

Put context areas inside the main references tree with documents directly in each area.
Use `references/api-reference/example.md`, never
`references/api-reference/references/example.md`.
Do not turn an area such as scripting-api into a separate product because it has a router.

The main root has references, assets, scripts and evals. Empty template folders use
.gitkeep and belong only at the main root or explicitly recognized product roots.
A genuine multi-product collection can contain product skills with their own trees.
Do not invent additional folders or remove populated folders during scaffold cleanup.

Repair organization before flattening. Check every ancestor, including separated,
case-varied and singular/plural repeats. `references/reference`, `orders/order`,
`handlers/handler` and `references/topics/reference` are redundant nesting too.
Use the actual subject to name an area, such as `references/language` for a programming
language's definition. Preserve distinct API class ownership when reorganizing classes.
If a redundant layer remains after organization, combine it while preserving contents.
If names collide, compare both contents, preserve distinct subjects and update indexes.
Never overwrite the destination or append a hash/counter to avoid the decision.

Name every file for its actual content after splitting. No arbitrary word-count limit.
Prefer `client-to-server-message-lifecycle.md` and
`server-to-client-message-lifecycle.md` over two direction folders hiding the same vague name.
Use categories when many related topics warrant a shared folder, without repeating
unnecessary words in every descendant path.

Apply the owner profile to every shipped file and folder, including references,
catalogs, binaries, scripts and empty directories. These are local authoring limits,
not additional Agent Skills frontmatter fields or interchange requirements.

| Measurement | Target | Hard limit |
| --- | --- | --- |
| Filename, including extension | 48 characters | 64 characters |
| Each folder name | 48 characters | 64 characters |
| Complete repository-relative file path | 100 characters | 160 characters |
| Directory levels for a single skill | 4 | 4 |
| Directory levels for a declared skill collection | 4 | 6 |

Count Unicode code points and one slash per path separator. Measure from the whole
collection root, including product folders; a product entrypoint does not reset the
path budget. Exclude the temporary staging parent from this measurement.
Only a collection with valid nested skills declares string metadata
`skill-type: collection` in its root frontmatter. Omit it for single skills.
The verifier cross-checks the declaration against nested `SKILL.md` files.
An empty declaration or an invalid member cannot grant the six-level allowance.
Do not create artificial subskills to obtain extra depth.
Targets guide choices; only exceeding a hard limit fails verification.
Shorten redundant ancestor wording after reading the subject. Do not truncate names,
append counters, raise limits or require Git long-path mode to hide a failing path.
Check the intended installation prefix separately for host-specific absolute limits.

Use `form-submission-actions.md` and `report-scheduling-actions.md` when those
are distinct owners. Preserve a genuine identifier such as a named protocol version;
review deterministic ordinal warnings rather than mechanically stripping digits.

Record every path mapping. Update Markdown, HTML, fragments, catalogs, images and
cross-product routes. Passing link checks does not establish correct subject ownership.
