# Analysis contract and supported inputs

Rubric v2 and parsers `srs-2` / `uml-2` are introduced by M2. Findings are evidence to review; neither a clean report nor a high score proves correctness.

## Scope and grades

Choose a scope when creating a project. **Requirements only** evaluates the SRS; UML and traceability are not applicable. **Requirements and architecture** requires an SRS plus use-case, class, and sequence diagrams. Each absent required upload blocks starting that profile. Deterministic analysis is the default and requires no model service. AI analysis is explicit and requires a configured provider; mock output is not a substitute for an AI assessment.

For requirements and UML, raw percentage is `max(0, 100 - severity_penalty / eligible_elements * 10)`. Configured critical/major/minor penalties are 15/5/2. System warnings and AI failures are not document defects. Trace percentage measures covered source/relation obligations, including inferred candidates, rather than how many links were newly inserted. Confirmed coverage is recorded separately. A lexical similarity value is not a probability of correctness.

Requirements-only reviews give the requirements category 100% weight. Architecture reviews use 40% requirements, 30% UML, and 30% traceability. Each category exposes its raw percentage, denominator, weight, and weighted contribution. No extracted requirements, missing evaluated categories, parser warnings, or failed requested AI checks suppress the overall grade. Available category results remain visible as partial evidence. Reviewer decisions do not silently change the raw machine score. Confirmed coverage in a score is a snapshot at analysis time; current link decisions are shown in the matrix.

Legacy scores retain their original values and have no v2 details. Do not compare them with v2 scores. Comparability also requires the same scope and evaluated diagram set. Immutable run history is implemented. Review decisions are stored separately and do not recalculate the published machine score.

## Extraction

DOCX paragraphs and tables are read in body order. Heading styles and numbered headings set the current section. Table headers named ID/Identifier/Requirement ID and Requirement/Statement/Description identify the statement columns; rows without recognized headers are combined conservatively. Merged cells are deduplicated within a row. Requirements use whole-word `shall` or `must`, or a leading authored ID in the supported FR/NFR/REQ/UC/R numeric family. Wrapped incomplete statements can continue in lowercase text; independent prose is not appended after a completed sentence.

Every occurrence has an internal identity, even when an authored ID is absent or duplicated. Authored IDs remain available for display and duplicate checks. Findings and extraction records preserve paragraph/table row or PDF page/line spans and artifact identity. PDF page breaks can continue an incomplete statement across repeated headers and page numbers. Image-only pages and suspected tables/columns generate warnings; OCR and reliable multi-column reading are not implemented. DOCX text boxes, embedded images, headers/footers, and nested tables are outside the supported extraction scope.

NFR classification includes its reason and confidence category. Numeric-threshold checks apply to performance and availability claims. A verifiable encryption/access-control requirement does not need an invented number. Any proposed acceptance target needs a stakeholder source.

## UML subset

Supported declarations include actors, use cases, classes/interfaces, namespaces/packages, and sequence participants. Quoted labels and aliases are retained as separate symbol identities. Repeated display labels are diagnosed without collapsing their occurrences. Inline use cases `(Name)` and actors `:Name:` are supported. Relationship endpoints resolve through the symbol table.

Class operations retain visibility, parameters, return type, and argument count. Sequence calls resolve their receiving participant/class and supported overload arity; an operation on another class cannot satisfy the call. This is not a type checker. Dashed reply messages are excluded from operation-call checks. Unsupported structural syntax produces a warning. Templates/generics, macros/preprocessors, activity/component diagrams, and arbitrary PlantUML syntax are not guaranteed. PlantUML is never executed, and external includes are rejected.

Tracing checks all available supported pairs, uses exact normalized authored-ID tokens, and records inference method and transitive path evidence. FR-1 does not match FR-10. Graph traversal terminates in cycles and excludes rejected/stale links from reviewed coverage. Requirements/use-case links, use-case/sequence links, sequence orphans, and classes without a requirement path are checked where applicable. Legacy decisions are mapped only when endpoints resolve uniquely; otherwise they become stale.

## Resource limits and publication

The operating defaults are 1,000 requirements and 2,000 UML elements, in addition to the upload/page/character/ZIP budgets in the development guide. SRS and UML analysis parsing both run in killable subprocesses with a wall-time limit and Linux address-space cap. These are conservative defaults, not measured deployment capacity.

A result is built before publishing findings, extraction, links, score, and status in one transaction. A fatal reanalysis failure preserves the prior report and gives an actionable error. Active reports poll automatically. Durable execution and immutable revisions are implemented; see the worker and revision guides.

## Verification limits

The regression suite includes real DOCX and PDF fixtures, aliases/overloads, unsupported syntax, missing/duplicate IDs, graph cycles, partial grades, reviewer persistence, and failure recovery. The small original evaluation dataset is preserved and counted by occurrence in `backend/eval/results.md`. Its old generic NFR labels disagree with the narrower threshold rule; this is disclosed rather than relabelled to increase the score. Independent annotation, held-out accuracy, browser accessibility/usability, and load testing remain release gates.
