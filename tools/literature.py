"""MCP tools: scientific literature search via PubMed and Europe PMC."""
from __future__ import annotations

from typing import Any

from mcp_app import mcp
from services import europepmc, pubmed
from services.http_client import NotFoundError, UpstreamAPIError


@mcp.tool()
async def search_pubmed(query: str, limit: int = 10) -> dict[str, Any]:
    """
    Search PubMed for scientific articles.

    Args:
        query: A PubMed query, e.g. 'TP53 AND apoptosis' or a plain gene name.
        limit: Max number of results.
    """
    try:
        papers = await pubmed.search(query, limit=limit)
        return {"query": query, "count": len(papers), "papers": papers}
    except (NotFoundError, UpstreamAPIError) as exc:
        return {"error": str(exc)}


@mcp.tool()
async def latest_papers(gene_or_protein: str, limit: int = 10) -> dict[str, Any]:
    """
    Get the most recently published PubMed papers mentioning a gene or protein.

    Args:
        gene_or_protein: Gene symbol or protein name.
        limit: Max number of results.
    """
    try:
        papers = await pubmed.latest_papers(gene_or_protein, limit=limit)
        return {"gene_or_protein": gene_or_protein, "count": len(papers), "papers": papers}
    except (NotFoundError, UpstreamAPIError) as exc:
        return {"error": str(exc)}


@mcp.tool()
async def protein_reviews(gene_or_protein: str, limit: int = 10) -> dict[str, Any]:
    """
    Get review articles (Publication Type: Review) about a gene or protein.

    Args:
        gene_or_protein: Gene symbol or protein name.
        limit: Max number of results.
    """
    try:
        papers = await pubmed.protein_reviews(gene_or_protein, limit=limit)
        return {"gene_or_protein": gene_or_protein, "count": len(papers), "papers": papers}
    except (NotFoundError, UpstreamAPIError) as exc:
        return {"error": str(exc)}


@mcp.tool()
async def clinical_trials(gene_or_protein: str, limit: int = 10) -> dict[str, Any]:
    """
    Get clinical-trial publications (Publication Type: Clinical Trial) mentioning
    a gene or protein.

    Args:
        gene_or_protein: Gene symbol or protein name.
        limit: Max number of results.
    """
    try:
        papers = await pubmed.clinical_trials(gene_or_protein, limit=limit)
        return {"gene_or_protein": gene_or_protein, "count": len(papers), "papers": papers}
    except (NotFoundError, UpstreamAPIError) as exc:
        return {"error": str(exc)}


@mcp.tool()
async def search_europepmc(query: str, limit: int = 10) -> dict[str, Any]:
    """
    Search Europe PMC, which additionally covers preprints and full-text
    matches that PubMed alone misses.

    Args:
        query: A search query, e.g. gene name or free text.
        limit: Max number of results.
    """
    try:
        papers = await europepmc.search(query, limit=limit)
        return {"query": query, "count": len(papers), "papers": papers}
    except (NotFoundError, UpstreamAPIError) as exc:
        return {"error": str(exc)}


@mcp.tool()
def summarize_paper(title: str, abstract: str) -> dict[str, Any]:
    """
    NOT YET IMPLEMENTED as an LLM summary. This currently returns the raw
    inputs; wiring this to an actual summarizer means calling out to a
    language model (e.g. the Anthropic API) from within this tool, which is
    listed under 'AI-powered summaries' in the future-enhancements roadmap.

    Args:
        title: Paper title.
        abstract: Paper abstract text.
    """
    return {
        "implemented": False,
        "title": title,
        "abstract_length": len(abstract),
        "note": "Wire this to an LLM call (see docs/ARCHITECTURE.md) for real summarization.",
    }
