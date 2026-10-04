"""ClinVar variant data via NCBI E-utilities. Free; NCBI_EMAIL recommended, not required."""
from __future__ import annotations

from typing import Any

from config import settings
from utils.cache import async_cached
from utils.parser import parse_clinvar_esummary, parse_ncbi_esearch_ids

from .http_client import request_json

SERVICE = "clinvar"


def _identity_params() -> dict[str, str]:
    params = {"tool": "protein-research-mcp", "email": settings.ncbi_email}
    if settings.ncbi_api_key:
        params["api_key"] = settings.ncbi_api_key
    return params


@async_cached("clinvar.variants", ttl_seconds=settings.ttl_default_seconds)
async def get_variants(gene_symbol: str, limit: int = 20) -> list[dict[str, Any]]:
    """Fetch ClinVar variant records associated with a gene symbol."""
    search_params = {
        "db": "clinvar",
        "term": f"{gene_symbol}[gene]",
        "retmax": limit,
        "retmode": "json",
        **_identity_params(),
    }
    search_raw = await request_json(
        SERVICE, "GET", f"{settings.clinvar_eutils_base}/esearch.fcgi", params=search_params
    )
    ids = parse_ncbi_esearch_ids(search_raw or {})
    if not ids:
        return []

    summary_params = {
        "db": "clinvar",
        "id": ",".join(ids),
        "retmode": "json",
        **_identity_params(),
    }
    summary_raw = await request_json(
        SERVICE, "GET", f"{settings.clinvar_eutils_base}/esummary.fcgi", params=summary_params
    )
    return parse_clinvar_esummary(summary_raw or {})
