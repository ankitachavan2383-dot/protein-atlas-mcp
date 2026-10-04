"""PubMed literature search via NCBI E-utilities. Free; NCBI_EMAIL recommended, not required."""
from __future__ import annotations

from typing import Any

from config import settings
from utils.cache import async_cached
from utils.parser import parse_ncbi_esearch_ids, parse_pubmed_esummary

from .http_client import request_json

SERVICE = "pubmed"


def _identity_params() -> dict[str, str]:
    params = {"tool": "protein-research-mcp", "email": settings.ncbi_email}
    if settings.ncbi_api_key:
        params["api_key"] = settings.ncbi_api_key
    return params


@async_cached("pubmed.search", ttl_seconds=settings.ttl_pubmed_seconds)
async def search(query: str, limit: int = 10, sort: str = "relevance") -> list[dict[str, Any]]:
    """Search PubMed and return flattened article summaries."""
    search_params = {
        "db": "pubmed",
        "term": query,
        "retmax": limit,
        "retmode": "json",
        "sort": sort,
        **_identity_params(),
    }
    search_raw = await request_json(
        SERVICE, "GET", f"{settings.pubmed_eutils_base}/esearch.fcgi", params=search_params
    )
    ids = parse_ncbi_esearch_ids(search_raw or {})
    if not ids:
        return []

    summary_params = {"db": "pubmed", "id": ",".join(ids), "retmode": "json", **_identity_params()}
    summary_raw = await request_json(
        SERVICE, "GET", f"{settings.pubmed_eutils_base}/esummary.fcgi", params=summary_params
    )
    return parse_pubmed_esummary(summary_raw or {})


async def latest_papers(gene_or_protein: str, limit: int = 10) -> list[dict[str, Any]]:
    return await search(f"{gene_or_protein}[Title/Abstract]", limit=limit, sort="pub_date")


async def protein_reviews(gene_or_protein: str, limit: int = 10) -> list[dict[str, Any]]:
    return await search(f"{gene_or_protein}[Title/Abstract] AND review[Publication Type]", limit=limit)


async def clinical_trials(gene_or_protein: str, limit: int = 10) -> list[dict[str, Any]]:
    return await search(
        f"{gene_or_protein}[Title/Abstract] AND clinical trial[Publication Type]", limit=limit
    )
