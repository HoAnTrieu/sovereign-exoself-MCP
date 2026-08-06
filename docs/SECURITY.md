# Security

Secrets are environment-only. Memory rejects credential-shaped strings and export contains active safe records only. No input reaches shell evaluation or dynamic Python evaluation. Requests have Pydantic length limits; provider calls have configurable retry/timeout limits; workers are capped at four. Model prompts and raw conversations are not logged or returned.
