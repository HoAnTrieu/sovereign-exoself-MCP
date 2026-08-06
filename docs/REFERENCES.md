# References

Accessed 2026-08-03.

| Title | URL | Relevant section | Installed decision |
|---|---|---|---|
| MCP Python SDK | https://github.com/modelcontextprotocol/python-sdk | v2 server/stdin transport | `mcp==2.0.0`, `MCPServer.run_stdio_async` |
| MCP Python docs | https://py.sdk.modelcontextprotocol.io/ | stdio API | official transport |
| MCP protocol | https://modelcontextprotocol.io/ | tools | exactly three tools |
| OpenCode MCP | https://opencode.ai/docs/mcp-servers | local server config | separate command-array snippet |
| OpenCode config | https://opencode.ai/docs/config/ | global config | `~/.config/opencode/opencode.json` |
| AionUI MCP guide | https://github.com/iOfficeAI/AionUi/wiki/MCP-Configuration-Guide | mcpServers | separate string command snippet |
| LiteLLM | https://docs.litellm.ai/docs/ | adapter | `litellm==1.95.0` |
| LiteLLM OpenRouter | https://docs.litellm.ai/docs/providers/openrouter | prefix and key | `openrouter/` model normalization |
| OpenRouter fallbacks | https://openrouter.ai/docs/guides/routing/model-fallbacks | fallback order | platform is fallback authority |
| OpenRouter providers | https://openrouter.ai/docs/guides/routing/provider-selection | allow fallbacks | no nested routing loop |
| OpenRouter errors | https://openrouter.ai/docs/api/reference/errors-and-debugging | retryability | transient-only local retry |
