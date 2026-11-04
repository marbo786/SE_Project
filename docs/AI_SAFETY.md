# AI safety checkpoints (M5a/M5b)

AI mode is optional. Deterministic mode makes no provider calls. Unknown provider names fail closed; mock providers are prohibited in production. Remote provider calls remain text-only and cannot invoke tools or select projects.

All application completions use the gateway. Both prompt strings pass through email, phone and long numeric identifier redaction. This is pattern-based minimization, not a guarantee that arbitrary confidential prose is anonymized. Inputs are limited to 24,000 characters, responses to 16,000 characters, provider calls to 60 seconds, and transport retries to at most three (environment settings control limits). Groq caps output at 2,048 tokens. Incomplete provider output is rejected.

Each attempted request reserves an `llm_calls` row under a project write lock before transmission. Successful, failed and interrupted requests consume the configured project request budget (default 50); historical non-cache `llm_logs` also count. New accounting rows contain only scope, model, hashes, status, timing and usage, never prompt or completion bodies. Legacy rows remain intact and are never used as cache entries. Minimal accounting is retained until project purge so retention cannot reset the lifetime request budget.

`LLM_RUN_TOKEN_BUDGET` defaults to 100,000. Each attempt reserves prompt UTF-8 byte length plus the 2,048-token output allowance, a conservative admission estimate rather than measured usage. Known nonnegative provider-reported usage replaces that estimate. Missing usage, failed requests and worker interruption retain the reservation with nullable measured counts and `reserved_unknown` provenance. Retries and recovered workers share the persisted run budget. Calls outside a run use a project-wide token budget. Reports show measured and unknown usage separately; neither is represented as a dollar price.

Validated testability/conflict responses may be cached only inside a sealed run context. Cache keys include owner, project, sealed input hash (artifact hashes and edits), analysis versions, provider/model, exact redacted prompt hash and schema version. Schema and occurrence/reference checks run before caching and again on every hit. Malformed, wrongly scoped or expired entries are removed and fetched afresh. Repair calls have no cache validator and bypass caching. Cached response bodies remain in their redacted provider form; confidential prose can still remain, so the cache is private project data, not anonymized public data.

`LLM_CACHE_TTL_SECONDS` defaults to 86,400 (one day), permits at most seven days, and zero disables caching. Expired entries are never served. Writes remove expired entries for that project. For inactive projects, schedule `python scripts/prune_ai_cache.py --apply` from `backend/`; omit `--apply` for a dry run. Project purge deletes both cache and accounting records. A cache hit records zero provider tokens and does not consume the provider-request budget.

Deployment requires stopping old API/workers and running `alembic upgrade head` before restarting. Migration `20261104_ai` is additive and does not reinterpret or delete historical logs. No existing user database was migrated during development.

Testability responses require strict fields and exactly one result per submitted occurrence ID. Repeated authored IDs are mapped by occurrence and source. Conflict results reject unknown IDs, self-pairs and duplicates. Each reported conflict is a candidate for human review, and an empty list is not proof that the document is consistent. Large documents exceeding the input limit produce partial analysis rather than silently dropping input.

Rewrite retries retain the original requirement. Checks cover normative structure, actor, numbers/units, negation/exception markers, original terms, and deterministic rules using classification inferred from the original text. These conservative lexical checks can reject valid paraphrases and cannot prove equivalent intent. All suggestions require human review; none is applied automatically. The report shows the individual checks. Missing metrics must be obtained from a stakeholder; invented thresholds do not pass. Provider or budget failure makes requested AI analysis partial. Worker cancellation/lease loss is never swallowed by repair.

## Remaining M5 work

- Monetary budgets with configured model pricing and explicit unknown timeout cost; token reservations are not dollar estimates.
- Token-aware batching, explicit coverage summaries and benchmarked conflict candidate retrieval recall.
- Rich source/subtype/neighbour context, targeted semantic checks, and evidence quote validation.
- Persisted accept/edit/reject suggestion decisions and explicit application to a new draft.
- Expanded prompt-injection fixtures and opt-in live-provider evaluation. No live provider calls were used to qualify this checkpoint.
