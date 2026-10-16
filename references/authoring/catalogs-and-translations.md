# Catalogs and translations

Open when writing context routes, topics.json or a language selector.

Markdown routes must work for clients that never read topics.json. Catalogs are a
portable library convention, not an Agent Skills discovery standard.
Include only material present inside this skill. Every summary is an actionable
“Open when ...” sentence, with a meaningful topic name and precise file path.

Group content by context type in Context Router, reference indexes and topic catalogs.
Use subject and workflow routes in task order, never alphabetic buckets or name ranges.
When a group exceeds 100 physical lines, subdivide it by meaningful context while
preserving every destination. Do not split it into fixed-size or numbered batches.

Catalogs record schema_version and topics. Resolve item files from their owning skill
or area root. An optional owner field may explicitly name that root (`.` for the main
skill); it is not required for existing catalogs. Otherwise infer the skill root from
its references/topics.json location, or use the containing area for an area catalog.
Markdown and HTML links resolve from their containing file; never compare basenames.
Focused area catalogs may use their containing area as owner. Do not escape the skill.

The final catalog entry is always Reference Language Selection, with a generic trigger:
“Open when you need a language version of references other than English.”
Use generic keywords such as “reference language” and “translated references”. No language-specific
discovery entry. Place the language selector last in reference indexes too.

Route SKILL.md to the language selector, then to the requested translated reference.
Prefer explicit reference-language choice, otherwise the request language. If unavailable,
use English and disclose the fallback. Response language is a separate choice.
List actual translations only, map each to its English topic and preserve version context.
Do not claim all references are translated because one Spanish file exists.

Keep the selector within 100 physical lines. A large language collection can route through
topic or locale indexes whose links are real and whose scope is clear.
Do not duplicate language-selection instructions in Context Router.

The renderer accepts complete translated content and explicit mappings. It does not
translate, guess coverage or choose a locale on behalf of the user.
