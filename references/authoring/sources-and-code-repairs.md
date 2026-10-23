# Sources and code repairs

Open when source extraction, examples or technical contracts appear defective.

Capture official documentation for the relevant version with URL, retrieval date,
content hash and license context. Keep evidence outside the shipped skill.
A downloaded stage may contain extraction damage; compare against fetched sources.
Source agreement alone does not establish correctness: upstream examples can be wrong.

Review code for flattened newlines, comments swallowing imports or calls, wrong fence
languages, missing imports, incorrect method/property names, incomplete declarations,
missing setup and lost callbacks. Check inline literals, HTML components and image URLs.
Review contracts for lost parameter descriptions, return values and changed namespace case.

Example: a JavaScript line comment joined to `import` or `invoke()` can silently disable
the example. Restore the complete code and keep npm and global-API alternatives distinct.
Example: an instrument may require `continuous_sweep_enabled`, while assignment to
`continuous_sweep` compiles but fails to configure the instrument. Test the actual property.
Example: a delta marker numbered two may be the valid default. Check its implementation
before “correcting” it; keep this as a negative control in the regression suite.

Record each correction, exact affected paths, source evidence and behavior check.
Use syntax checks for complete code in its actual language/version. Use strict mocks
for calls and ownership when the host is unavailable. Native execution is separate.
Do not execute fetched or candidate code automatically. Review it, select a bounded
test and use a disposable environment with explicit capabilities.

Link the source of any example longer than 40 lines instead of copying it; keep shorter
general-purpose examples without upstream license headers. The disclaimer is a source
pointer, not a legal determination that arbitrary copied source may be republished. Do not ship scraped
corpus artifacts, extraction debris or skill-authoring instructions in product references.

For changed code, the decision record requires captured evidence and a behavior-check
statement. That declaration does not prove a test ran: retain actual results and review them.
