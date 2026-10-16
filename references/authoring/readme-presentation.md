# Main README presentation

Open when drafting or revising a main skill README, its branding, summary, trigger paragraph or subskill list.

This is the owner's current draft library presentation pattern, not an Agent Skills specification requirement. Refine it through owner review; do not label the complete layout final until the owner settles it. Keep the accepted reusable layout and branding assets together when that decision is made.

## Required opening order

1. One `#` heading with the human-readable skill title.
2. The inline Mermaid branding chart immediately below that heading.
3. A brief professional paragraph summarizing the skill's actual purpose and useful coverage.
4. A second prose paragraph containing the exact decoded `description` value from that skill's `SKILL.md` YAML frontmatter.
5. The most useful capabilities and a complete linked list of actual subskills, when present.

The chart is not a prose paragraph. Do not insert another paragraph, caption or section heading between the professional brief and the trigger paragraph. Do not paraphrase the trigger, include YAML quoting, or add a prefix such as "Use this skill:". Parse folded YAML correctly. When the trigger changes, update the README's second paragraph with it.

## Useful remainder

Explain concrete tasks the bundled material helps with and link to useful routes. Prefer a concise table or short list over repeating the trigger. Describe the actual interpretation, restructuring and source-checking work without claiming universal correctness, completeness or measured performance.

For a package with subskills, list every included subskill with its human-readable name, relative README.md link and concise purpose. Review nested SKILL.md files and existing routers to distinguish product subskills from reference areas. Label reference areas accurately; do not turn ordinary topic folders into imaginary subskills. Omit an empty subskills section for a single skill.

Keep relevant start/use instructions and version boundaries. Use the exact source/license section below and preserve license and attribution files with their source material. Preserve useful package-specific details. Nested operational READMEs retain their own purpose and do not automatically receive this main README layout.

Subskill overview links point to the target skill's README.md; for example, `references/agentfs/README.md`. Task links point to the relevant Markdown reference or readable subject index. Check the destination's contents and follow its routes to the promised material. Do not send README readers through JSON or JSONL routing catalogs, or create Markdown wrappers that merely link to those catalogs. Keep legitimate catalogs for agent routing. Use SKILL.md links only when explicitly directing readers to agent instructions.

## Reusable assets

- Open when laying out a main README. [README template](../../assets/readme.md.template).
- Open when constructing its shared branding chart. [Mermaid header template](../../assets/readme-header.mmd.template).

Replace all placeholders. The README template contains a slot for the chart body; insert the Mermaid template there inside the existing mermaid fence. Keep the heading first. Author the brief and useful capabilities from inspected package contents. The trigger comes from SKILL.md, not model inference.

## Branding

Use the Topic constellation design: KAIZEN SKILL LIBRARY in cyan on a navy block, a blue skill-title panel, and up to three connected capability capsules. Preserve the shared colors, shapes and brand wording. Change the title and truthful subject labels. Use the amber accent for one capsule. These capsules are a visual summary, not the complete subskill inventory.

Keep inline Mermaid so the README carries its own chart source. If labels need quotes or special characters, encode them using supported Mermaid syntax and render-check the result. Keep the ordinary Markdown title and explanatory text useful when a reader cannot render diagrams.

## Review checks

- Confirm the H1 precedes the chart and the first two prose paragraphs follow in order.
- Compare the second paragraph exactly with the parsed frontmatter description.
- Check every subskill overview link targets its README.md and that the list matches the actual package.
- Verify task routes reach the promised Markdown material without requiring JSON catalogs. Check coverage and continuation links, not only file existence.
- Compare the complete Sources and license section against the two-paragraph template; reject all extra text.
- Verify useful claims, attribution, local links and LF endings; leave no template tokens.
- Render the actual chart after substitutions. Distinguish local rendering from a hosted GitHub test.
- Preserve the staged review/deployment gate. Approval of a branding choice alone does not approve unrelated README prose or skill changes.

The library's 100-line reference cap applies to this reference; it is not a new global README length limit. No reusable script is needed merely to store this pattern. If generation is automated later, test paragraph equality and layout rather than treating placeholder substitution as editorial review.

## Exact Sources and license section

End every root and nested README with exactly this section and these two paragraphs. Change only the official documentation URL and the relative LICENSE destination:

```markdown
## Sources and license

Skill reference documentation is interpreted content for use in open source projects. Check against [official documentation sources]({{official_source_url}}) when dealing with defects or issues that may come up from interpreting this skill's references.

Licensed under **AGPL-3.0**; see [LICENSE]({{license_relative_path}}). Part of the [Agent Kaizen](https://github.com/LevyBytes/agent-kaizen) skill library.
```

No additional paragraphs, attribution lists, bundled-license lists, subheadings or alternate licensing prose belong in this section. Do not add a duplicate license section elsewhere in the README. Preserve the package's license and source-notice files with their source material. Use portable relative LICENSE paths, never VS Code preview URLs. Verify that the official documentation URL opens the relevant primary documentation.

## Capability labels and supporting documents

Chart capsules name distinct tasks or capabilities supported by the bundled material. Avoid vague labels, document types and execution environments used as substitutes for capabilities. Use fewer than three capsules when the skill has fewer distinct capabilities; a pointer-only reference can have one.

Use README.md for skill presentation. Evaluation run instructions belong in evals/EVALS.md. Give tutorial and operational guides purpose-based filenames; do not borrow a parent activation paragraph to present them as subskills.
