"""MCP tools: protein/gene search against UniProt."""
from __future__ import annotations

from typing import Any

from mcp_app import mcp
from services import uniprot
from services.http_client import NotFoundError, UpstreamAPIError
from utils.validators import is_uniprot_accession, normalize_identifier


@mcp.tool()
async def search_protein(query: str, organism_id: int | None = 9606, limit: int = 10) -> dict[str, Any]:
    """
    Search UniProtKB by protein name, gene name, or free text.

    Args:
        query: Search text, e.g. "tumor suppressor p53" or "TP53".
        organism_id: NCBI taxonomy ID to restrict results (default 9606 = human). Pass None for all organisms.
        limit: Max number of results (1-50).
    """
    limit = max(1, min(limit, 50))
    try:
        results = await uniprot.search(query, organism_id=organism_id, limit=limit)
        return {"query": query, "count": len(results), "results": results}
    except (UpstreamAPIError, NotFoundError) as exc:
        return {"error": str(exc)}


@mcp.tool()
async def search_gene(gene_name: str, organism_id: int = 9606, limit: int = 5) -> dict[str, Any]:
    """
    Search for a protein by its gene symbol (e.g. 'TP53', 'EGFR', 'BRCA1').

    Args:
        gene_name: HGNC-style gene symbol.
        organism_id: NCBI taxonomy ID (default 9606 = human).
        limit: Max number of results.
    """
    try:
        results = await uniprot.search_by_gene(gene_name, organism_id=organism_id, limit=limit)
        return {"gene_name": normalize_identifier(gene_name), "count": len(results), "results": results}
    except (UpstreamAPIError, NotFoundError) as exc:
        return {"error": str(exc)}


@mcp.tool()
async def search_uniprot(accession: str) -> dict[str, Any]:
    """
    Fetch a single UniProtKB entry directly by accession (e.g. 'P04637').

    Args:
        accession: A UniProt accession number.
    """
    accession = normalize_identifier(accession)
    if not is_uniprot_accession(accession):
        return {"error": f"'{accession}' does not look like a valid UniProt accession."}
    try:
        entry = await uniprot.get_entry(accession)
        return entry
    except NotFoundError:
        return {"error": f"No UniProt entry found for accession '{accession}'."}
    except UpstreamAPIError as exc:
        return {"error": str(exc)}


@mcp.tool()
async def search_by_keyword(keyword: str, limit: int = 10) -> dict[str, Any]:
    """
    Broad free-text keyword search across UniProtKB (function, disease, keyword annotations).

    Args:
        keyword: Any search term, e.g. "kinase inhibitor resistance".
        limit: Max number of results.
    """
    try:
        results = await uniprot.search(keyword, organism_id=None, limit=limit)
        return {"keyword": keyword, "count": len(results), "results": results}
    except (UpstreamAPIError, NotFoundError) as exc:
        return {"error": str(exc)}
