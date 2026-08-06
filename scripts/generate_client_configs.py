"""Generate host-specific local MCP snippets for this checkout."""

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = str(ROOT / ".venv" / "bin" / "python")
DIST = ROOT / "dist"


def _load_dotenv() -> None:
    """Best-effort load of a .env file in the project root (if present)."""
    env_path = ROOT / ".env"
    if not env_path.is_file():
        return
    for raw_line in env_path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def _resolve_environment() -> dict[str, str]:
    """Return the runtime environment for the MCP server subprocess.

    Priority (highest wins): explicit env override -> .env file -> defaults.

    - `ollama`  : the default real provider (local, free, available out of the box).
    - `openrouter`: used automatically when OPENROUTER_API_KEY is available.
    - `mock`    : only when explicitly requested via SOVEREIGN_PROVIDER_MODE.
    """
    _load_dotenv()

    env = {"PYTHONUNBUFFERED": "1"}

    # Honour an explicit override if the user set one (e.g. SOVEREIGN_PROVIDER_MODE=mock).
    explicit_mode = os.environ.get("SOVEREIGN_PROVIDER_MODE")
    if explicit_mode and explicit_mode in {"mock", "ollama", "openrouter"}:
        env["SOVEREIGN_PROVIDER_MODE"] = explicit_mode
        # Surface ollama model selection only when relevant.
        if explicit_mode == "ollama":
            for key in (
                "SOVEREIGN_OLLAMA_MANAGER_MODEL",
                "SOVEREIGN_OLLAMA_WORKER_MODEL",
                "SOVEREIGN_OLLAMA_CRITIC_MODEL",
                "SOVEREIGN_OLLAMA_SYNTHESIZER_MODEL",
                "SOVEREIGN_OLLAMA_ARCHIVIST_MODEL",
            ):
                if os.environ.get(key):
                    env[key] = os.environ[key]
        if explicit_mode == "openrouter":
            # No secret is embedded here: the key is loaded at runtime from the
            # gitignored project `.env` by `settings.load_env_file`.
            pass
        return env

    # No explicit override: auto-select a real provider.
    if os.environ.get("OPENROUTER_API_KEY"):
        # Mode only — the key itself is picked up from `.env` at runtime.
        env["SOVEREIGN_PROVIDER_MODE"] = "openrouter"
    else:
        env["SOVEREIGN_PROVIDER_MODE"] = "ollama"

    return env


def main() -> None:
    """Write valid OpenCode and AionUI configuration files."""
    DIST.mkdir(exist_ok=True)
    environment = _resolve_environment()
    opencode = {
        "$schema": "https://opencode.ai/config.json",
        "mcp": {
            "sovereign-exoself": {
                "type": "local",
                "command": [PYTHON, "-m", "sovereign_exoself_mcp"],
                "cwd": str(ROOT),
                "environment": environment,
                "enabled": True,
                "timeout": 30000,
            }
        },
    }
    aionui = {
        "mcpServers": {
            "sovereign-exoself": {
                "description": "Local durable personal council",
                "command": PYTHON,
                "args": ["-m", "sovereign_exoself_mcp"],
                "env": environment,
            }
        }
    }
    (DIST / "opencode.mcp.jsonc").write_text(json.dumps(opencode, indent=2) + "\n")
    (DIST / "aionui.mcp.json").write_text(json.dumps(aionui, indent=2) + "\n")
    (DIST / "install-summary.txt").write_text(
        f"cd {ROOT}\nuv sync --frozen\n"
        f"OpenCode: ~/.config/opencode/opencode.json\n"
        f"AionUI: import {DIST / 'aionui.mcp.json'}\n"
        f"{PYTHON} -m sovereign_exoself_mcp\n"
    )


if __name__ == "__main__":
    main()
