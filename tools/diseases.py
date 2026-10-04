"""MCP tools: disease and variant associations via ClinVar and Open Targets."""
from __future__ import annotations

from typing import Any

from mcp_app import mcp
from services import clinvar, opentargets
from services.http_client import NotFoundError, UpstreamAPIError


@mcp.tool()
async def get_diseases(gene_symbol: str, limit: int = 15) -> dict[str, Any]:
    """
    Get disease associations for a gene from Open Targets (aggregated evidence score).

    Args:
        gene_symbol: A gene symbol, e.g. 'APOE'.
        limit: Max number of associations to return.
    """
    try:
        diseases = await opentargets.get_disease_associations(gene_symbol, limit=limit)
        return {"gene_symbol": gene_symbol.upper(), "disease_count": len(diseases), "diseases": diseases}
    except (NotFoundError, UpstreamAPIError) as exc:
        return {"error": str(exc)}


@mcp.tool()
async def clinvar_variants(gene_symbol: str, limit: int = 20) -> dict[str, Any]:
    """
    Get ClinVar variant records for a gene, with clinical significance and conditions.

    Args:
        gene_symbol: A gene symbol, e.g. 'BRCA1'.
        limit: Max number of variants to return.
    """
    try:
        variants = await clinvar.get_variants(gene_symbol, limit=limit)
        return {"gene_symbol": gene_symbol.upper(), "variant_count": len(variants), "variants": variants}
    except (NotFoundError, UpstreamAPIError) as exc:
        return {"error": str(exc)}


@mcp.tool()
async def open_targets(gene_symbol: str, limit: int = 15) -> dict[str, Any]:
    """Alias for get_diseases, explicit about the Open Targets source."""
    return await get_diseases(gene_symbol, limit=limit)


@mcp.tool()
async def gene_disease_score(gene_symbol: str, disease_name: str) -> dict[str, Any]:
    """
    Look up the Open Targets association score between a gene and a specific disease.

    Args:
        gene_symbol: A gene symbol, e.g. 'EGFR'.
        disease_name: A disease name to search for within the gene's associations, e.g. 'lung carcinoma'.
    """
    try:
        diseases = await opentargets.get_disease_associations(gene_symbol, limit=50)
        match = next((d for d in diseases if disease_name.lower() in d["disease_name"].lower()), None)
        if not match:
            return {"gene_symbol": gene_symbol.upper(), "disease_name": disease_name, "found": False}
        return {"gene_symbol": gene_symbol.upper(), "found": True, **match}
    except (NotFoundError, UpstreamAPIError) as exc:
        return {"error": str(exc)}


@mcp.tool()
async def associated_cancers(gene_symbol: str) -> dict[str, Any]:
    """
    Filter a gene's disease associations to cancer/neoplasm-related conditions.

    Args:
        gene_symbol: A gene symbol, e.g. 'TP53'.
    """
    try:
        cancers = await opentargets.associated_cancers(gene_symbol)
        return {"gene_symbol": gene_symbol.upper(), "cancer_count": len(cancers), "cancers": cancers}
    except (NotFoundError, UpstreamAPIError) as exc:
        return {"error": str(exc)}
