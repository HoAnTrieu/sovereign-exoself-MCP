"""Executable stdio entrypoint."""

import sys

import anyio

from sovereign_exoself_mcp.server import create_server


async def run() -> None:
    """Run the official MCP stdio transport."""
    await create_server().run_stdio_async()


def main() -> None:
    """Handle local configuration checks and server startup."""
    if "--check" in sys.argv:
        create_server()
        print("configuration ok", file=sys.stderr)
        return
    anyio.run(run)


if __name__ == "__main__":
    main()
