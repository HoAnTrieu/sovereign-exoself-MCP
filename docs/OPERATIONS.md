# Operations

Run `bash scripts/test.sh` before release. `scripts/install.sh` syncs dependencies and writes host snippets only; it never changes host configuration. Run `.venv/bin/python -m sovereign_exoself_mcp` for stdio service operation. Database files must be user-readable only; the repository enforces mode `0600` on new databases.
