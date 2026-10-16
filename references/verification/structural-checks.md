# Structural checks

Open when verifying a proposed or emitted skill package.

Run the bundled verifier against actual files, not only a source inventory or generator.
It parses YAML with duplicate-key rejection and Markdown with a CommonMark parser plus
tables. It checks supported fields, trigger descriptions, string metadata/date, exact
entrypoint sections, disclaimer, language-section exclusivity and root folder presence.

It checks LF/UTF-8 text, the 100-physical-line cap, repeated ancestor names, case collisions,
suspect ordinal/hash names, misplaced empty templates and heading-only fragments.
It enforces the [name and path bounds](../authoring/organization-and-naming.md):
64 characters per filename (including extension) or folder name, 160 characters
per repository-relative file path, four directory levels for single skills and six
for declared collections with valid nested entrypoints. Targets of 48, 100 and 4
produce warnings without failure. Counts use Unicode code points, not byte lengths.
All shipped file types and empty directories are included; product roots do not
reset the collection-relative budget. Temporary staging-parent length is excluded.
These hard failures cannot be waived through contextual dispositions.
The root metadata `skill-type: collection` must agree with nested `SKILL.md`
contents. A false declaration, missing declaration or malformed member fails.
It resolves local Markdown/HTML links, explicit IDs and heading fragments, catalogs and
reachability from the main entrypoint. Product entrypoints must be reachable through routes.

Binary files are preserved; the text line cap applies to decoded reference material.
Heading slugs follow the bundled parser convention. Hosting platforms may use different
slug rules; prefer explicit IDs for ambiguous punctuation or duplicate headings.
External URLs are not fetched by verification. Review source availability separately.

The verifier cannot establish semantic naming, correct API ownership, completeness of
paraphrases, lawful reuse, activation quality or application behavior. Report those as
separate review/test results. “Structural checks passed” is not whole-skill certification.

Review grouping by context type separately: inspect the actual subject, API owner
and workflow of each routed document. Reject alphabetical buckets, lexical ranges
and arbitrary count-based groups. Check that route order follows the task.
Coverage and link checks cannot prove that a document belongs in its chosen group.
Preserve technical documentation about sorting; this rule governs organization.

Only suspect naming and custom-HTML findings allow contextual dispositions. Bind each
to path, current SHA-256, finding code and a specific rationale. Hard structural failures
cannot be waived. A stale or unmatched disposition is rejected. Examples that resemble
HTML may need escaping or inline code, not a waiver.

Keep the report's failed checks visible. Fix defective validators using positive and
negative fixtures, then rerun affected checks. Do not delete inconvenient findings.
See [the test strategy](../evaluation/regression-and-behavior.md).
