# Memory Model

SQLite is the only persistence service. Schema v1 includes `schema_version`, `sessions`, `runs`, `messages`, `memory_items`, `memory_sources`, `provider_calls`, and `outbox`. Memory uses normalized SHA-256 fingerprints for dedupe; FTS5 is preferred and tokenized `LIKE` ranking is the tested fallback. Delete is a durable soft delete. Outbox recovery runs at repository startup and is idempotent.
