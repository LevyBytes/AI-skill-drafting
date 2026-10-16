# Frontmatter and entrypoint

Open when writing a skill trigger, metadata or its main router.

Use name and description. Optional recognized fields are license, compatibility,
metadata and allowed-tools. Put custom string values under metadata; no top-level
covers or triggers. This profile also retires metadata.covers.
Preserve existing licensing; do not add a compulsory license field beyond agreed scope.

Name matches its containing directory: lowercase letters, digits and single hyphens,
1–64 characters. Description begins with an actionable “Use when ...” instruction,
is shorter than 1,024 characters, and describes recognizable user intents.
Include indirect requests where useful. Avoid a keyword inventory and competing topics.

```yaml
name: instrument-control
description: Use when connecting instruments, configuring measurements or debugging VISA communication.
metadata:
  last-updated: '2026-10-15'
```

Use the actual UTC date when updating; quote it so YAML retains a string.
Compatibility states real execution dependencies, not promotional claims.

For a collection that bundles genuine nested skills, add `skill-type: collection`
under the root's `metadata`. Omit this key for a single skill.
This is a custom owner-profile value within the standard metadata field, not an
Agent Skills-defined collection flag. Do not add a top-level field or a YAML boolean.
The declared collection must contain valid nested `SKILL.md` entrypoints; nested
entrypoints without the declaration, or a declaration without valid members, fail.
Collections permit six directory levels from the collection root; single skills
permit four. Product membership does not automatically require extra scaffolding.

Immediately after frontmatter, use exactly these headings in this order:

```markdown
# Context Router
# Language Translations
# Context For Open Source
```

Context Router uses meaningful “Open when ...” links into the root references tree.
Do not put language-selection prose there. Language Translations contains only
`[Reference Language Selection](references/languages.md)`.
An existing area entrypoint inside references uses `languages.md` instead.
Do not emit Gotchas, Verification or other entrypoint sections. Move useful subject
guidance into its references; new sections require an explicit owner decision.

The final section uses this exact sentence, changing only the official source URL:

Skill reference documentation is interpreted content for use in open source projects. Check against [official documentation sources](https://agentskills.io/specification) when dealing with defects or issues that may come up from interpreting this skill's references.

Use [the renderer template](../../assets/entrypoint.md.template), not another generator.
