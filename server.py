"""
Protein Research MCP Server - entry point.

Run with:
    uv run server.py
or:
    python server.py

Then point an MCP client (Claude Desktop, Claude Code, Cursor, etc.) at this
process. See README.md for client configuration examples.
"""
from __future__ import annotations

from config import log
from mcp_app import mcp

# Each import below registers that module's @mcp.tool()-decorated functions
# onto the shared `mcp` instance. The imports are load-bearing even though
# nothing in this file calls into them directly - do not let a linter remove them.
from tools import (  # noqa: F401,E402
    diseases,
    domains,
    interactions,
    literature,
    pathways,
    reports,
    search,
    sequence,
    structure,
)

if __name__ == "__main__":
    log.info("Starting protein-research-mcp server...")
    mcp.run()
