"""Europe PMC search service — complements PubMed with preprints & full-text search. No key required."""
from __future__ import annotations

from typing import Any

from config import settings
from utils.cache import async_cached

from .http_client import request_json

SERVICE = "europepmc"


@async_cached("europepmc.search", ttl_seconds=settings.ttl_pubmed_seconds)
async def search(query: str, limit: int = 10) -> list[dict[str, Any]]:
    """Search Europe PMC (includes preprints, PMC full text, and PubMed records)."""
    params = {"query": query, "format": "json", "pageSize": limit}
    raw = await request_json(SERVICE, "GET", f"{settings.europepmc_base}/search", params=params)
    results = (raw or {}).get("resultList", {}).get("result", [])
    return [
        {
            "id": r.get("id"),
            "source": r.get("source"),
            "title": r.get("title"),
            "authors": r.get("authorString"),
            "journal": r.get("journalTitle"),
            "pub_year": r.get("pubYear"),
            "doi": r.get("doi"),
            "is_open_access": r.get("isOpenAccess") == "Y",
            "url": f"https://europepmc.org/article/{r.get('source')}/{r.get('id')}"
            if r.get("id")
            else None,
        }
        for r in results
    ]
