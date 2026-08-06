import json
from pathlib import Path


def test_generated_configs_when_parsed_then_have_distinct_host_schemas() -> None:
    root = Path.cwd()
    opencode = json.loads((root / "dist" / "opencode.mcp.jsonc").read_text())
    aionui = json.loads((root / "dist" / "aionui.mcp.json").read_text())
    assert opencode["mcp"]["sovereign-exoself"]["type"] == "local"
    assert isinstance(opencode["mcp"]["sovereign-exoself"]["command"], list)
    assert "mcpServers" in aionui
    assert isinstance(aionui["mcpServers"]["sovereign-exoself"]["command"], str)
