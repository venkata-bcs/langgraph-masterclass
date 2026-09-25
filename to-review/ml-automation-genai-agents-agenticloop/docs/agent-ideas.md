# Agent ideas for this pipeline

Brainstormed extensions beyond the four core pipelines (genai_datagen,
automation_router, data_loader, schema_evolution).

1. **Data Quality / Validation Agent** — runs after `data_loader`, checks
   null rates, referential integrity (every `inventory.product_id` exists in
   `products`), value-range sanity (negative prices/quantities), and fails
   the run loudly instead of silently shipping bad joins.

2. **Schema Diff Reviewer (human-in-the-loop) Agent** — instead of
   `schema_evolution` auto-regenerating on any registry change, this agent
   posts a proposed diff (new columns/tables) and waits for approval before
   triggering regeneration. Useful once this moves from a demo to something
   touching real downstream consumers.

3. **Anomaly Detection Agent** — compares each new generation run's
   aggregate stats (row counts, price distributions, category mix) against
   a rolling baseline and flags runs that look statistically off.

4. **Reconciliation Agent** — after routing, verifies row counts and
   checksums between what `automation_router` moved and what `data_loader`
   actually ingested, catching partial writes or silently skipped files.

5. **Data Catalog / Documentation Agent** — reads `schema_registry.yaml` and
   the latest joined output, and auto-generates a data dictionary (column
   names, types, sample values, last-updated table) as markdown.

6. **Natural-Language Query Agent** — a thin LangGraph wrapper that takes a
   plain-English question, generates pandas/SQL against the latest joined
   dataset in `target-data/joined/`, executes it, and returns the answer.

7. **Cost / Usage Monitor Agent** — tracks which LLM provider in the
   `ollama_cloud -> groq -> openrouter` fallback chain actually served each
   request and how often fallback was needed, so provider outages or key
   expirations are visible before they silently degrade classification
   quality to the heuristic fallback.

8. **Retention / Archival Agent** — target-data and source-data accumulate a
   new timestamped file per run; this agent compacts or archives files older
   than N days/runs so storage doesn't grow unbounded.

9. **Notification Agent** — posts a summary (new files routed, schema
   changes detected, join row counts) to Slack/email/webhook after each
   pipeline run, so schema evolution or routing surprises don't require
   someone to check logs manually.

10. **Volume-Forecasting Agent** — looks at historical generation run sizes
    and adjusts the `--count` passed to `genai_datagen` to simulate realistic
    growth trends instead of a fixed row count every run.
