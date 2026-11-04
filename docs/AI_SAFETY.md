# AI safety checkpoint (M5a)

AI mode is optional. Deterministic mode makes no provider calls. Unknown provider names fail closed; mock providers are prohibited in production. Remote provider calls remain text-only and cannot invoke tools or select projects.

All application completions use the gateway. Both prompt strings pass through email, phone and long numeric identifier redaction. This is pattern-based minimization, not a guarantee that arbitrary confidential prose is anonymized. Inputs are limited to 24,000 characters, responses to 16,000 characters, provider calls to 60 seconds, and transport retries to at most three (environment settings control limits). Groq caps output at 2,048 tokens. Incomplete provider output is rejected.

Each attempted request reserves a project-scoped audit row under a project write lock before transmission. Successful, failed and interrupted requests consume the configured project request budget (default 50). `cache_hit` retains its historical name: `false` denotes a response with provider-reported usage; `pending_unknown_usage` and `failed_unknown_usage` denote unknown usage, not zero-cost calls. No new prompt or completion bodies are stored. Existing historical rows are left intact. A schema separating calls and validated cache entries remains pending; no raw legacy row is read as a cache entry.

Testability responses require strict fields and exactly one result per submitted occurrence ID. Repeated authored IDs are mapped by occurrence and source. Conflict results reject unknown IDs, self-pairs and duplicates. Each reported conflict is a candidate for human review, and an empty list is not proof that the document is consistent. Large documents exceeding the input limit produce partial analysis rather than silently dropping input.

Rewrite retries retain the original requirement. Checks cover normative structure, actor, numbers/units, negation/exception markers, original terms, and deterministic rules using classification inferred from the original text. These conservative lexical checks can reject valid paraphrases and cannot prove equivalent intent. All suggestions require human review; none is applied automatically. The report shows the individual checks. Missing metrics must be obtained from a stakeholder; invented thresholds do not pass. Provider or budget failure makes requested AI analysis partial. Worker cancellation/lease loss is never swallowed by repair.

## Remaining M5 work

- Separate call/cache schema with usage provenance, retention and owner/project/artifact/prompt/schema/model scoped validated caching with expiry.
- Run-level token and monetary budgets with explicit unknown timeout usage; current limits are request/character bounds, not dollar estimates.
- Token-aware batching, explicit coverage summaries and benchmarked conflict candidate retrieval recall.
- Rich source/subtype/neighbour context, targeted semantic checks, and evidence quote validation.
- Persisted accept/edit/reject suggestion decisions and explicit application to a new draft.
- Expanded prompt-injection fixtures and opt-in live-provider evaluation. No live provider calls were used to qualify this checkpoint.
