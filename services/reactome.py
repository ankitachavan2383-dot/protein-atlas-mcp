"""Reactome pathway database service. No API key required."""
from __future__ import annotations

from typing import Any

from config import settings
from utils.cache import async_cached

from .http_client import request_json

SERVICE = "reactome"


@async_cached("reactome.pathways", ttl_seconds=settings.ttl_default_seconds)
async def get_pathways(uniprot_accession: str, species: str = "Homo sapiens") -> list[dict[str, Any]]:
    """Fetch Reactome pathways that a UniProt-identified protein participates in."""
    url = f"{settings.reactome_base}/data/mapping/UniProt/{uniprot_accession}/pathways"
    raw = await request_json(SERVICE, "GET", url, params={"species": species})
    if not raw:
        return []
    return [
        {
            "id": entry.get("stId"),
            "name": entry.get("displayName"),
            "species": (entry.get("speciesName")),
            "url": f"https://reactome.org/content/detail/{entry.get('stId')}",
        }
        for entry in raw
    ]


async def pathway_summary(pathway_id: str) -> dict[str, Any]:
    """Fetch a short description for a single Reactome pathway (e.g. R-HSA-73894)."""
    raw = await request_json(SERVICE, "GET", f"{settings.reactome_base}/data/query/{pathway_id}")
    if not raw:
        return {}
    summation = raw.get("summation", [{}])
    return {
        "id": raw.get("stId"),
        "name": raw.get("displayName"),
        "description": summation[0].get("text") if summation else None,
        "url": f"https://reactome.org/content/detail/{pathway_id}",
    }
