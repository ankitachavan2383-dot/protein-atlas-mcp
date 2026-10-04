"""
The single shared FastMCP instance.

Every module in tools/ imports `mcp` from here and registers its functions
with `@mcp.tool()`. `server.py` imports each tools module purely for that
registration side effect, then calls `mcp.run()`. Keeping the instance in
its own tiny module (instead of in server.py) avoids a circular import
between server.py and tools/*.py.
"""
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "protein-research-mcp",
    instructions=(
        "Tools for protein research: search UniProt, analyze sequences, fetch AlphaFold/PDB "
        "structures, look up domains, protein-protein interactions, pathways, disease "
        "associations, and literature, plus a report generator that combines all of the above."
    ),
)
