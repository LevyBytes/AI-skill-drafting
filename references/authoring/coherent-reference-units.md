# Coherent reference units

Open when splitting or merging reference documents under the 100-line profile.

Count physical lines, including blanks, headings, fences, tables, metadata and navigation.
The limit is 100. Report the longest measured file separately; 97 is a measurement,
not a new limit. Do not flatten code or pack unrelated material onto long lines.

Use parser source coordinates to locate complete units, then read them in context.
Keep imports, preambles, setup, callbacks, signatures, parameter descriptions, return
values and dependent examples together. Avoid heading-only fragments and detached tables.
Do not mistake a heading inside a fence for a document boundary.

A complete 140-line example cannot fit through simple splitting. Either restructure it
into independently usable linked modules with explicit dependencies or report the exact
conflict. Do not truncate, silently summarize protected code or fabricate continuation files.

Model decisions name the units and boundaries. The renderer consumes complete content;
it refuses oversized references. It never invents a split based on bytes or a heading.
For a larger proposal, author explicit topic indexes and area catalogs; do not minify
a catalog merely to hide an oversized structure.

Preserve prose meaning and exact technical identifiers. Deliberate prose rewrites need
line-range review and an explanation. Preserved code is compared independently as parsed
code-block text, including language labels; full source files use exact text.
This protects examples, not prose meaning or every inline literal. Review those separately.

Tables belong to the API or procedure they describe. Link context explicitly when a
complete table is independent. A valid Markdown table can still describe the wrong owner.
Distinguish conceptual fragments from runnable examples; never claim every fragment compiles.
