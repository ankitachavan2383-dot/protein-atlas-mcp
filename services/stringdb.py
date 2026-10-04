"""STRING protein-protein interaction database. No API key required (caller identity is polite, not enforced)."""
from __future__ import annotations

from typing import Any

from config import settings
from utils.cache import async_cached

from .http_client import request_json

SERVICE = "string-db"


@async_cached("string.interactions", ttl_seconds=settings.ttl_default_seconds)
async def get_interactions(
    identifier: str, species: int = 9606, limit: int = 20, min_score: int = 400
) -> list[dict[str, Any]]:
    """
    Fetch STRING interaction partners for a gene/protein identifier.
    `species` is an NCBI taxonomy ID (default 9606 = human).
    `min_score` is STRING's combined confidence score, 0-1000 (400 = medium confidence).
    """
    params = {
        "identifiers": identifier,
        "species": species,
        "limit": limit,
        "required_score": min_score,
        "caller_identity": settings.string_caller_identity,
    }
    raw = await request_json(SERVICE, "GET", f"{settings.string_base}/json/network", params=params)
    if not raw:
        return []

    interactions = []
    for edge in raw:
        interactions.append(
            {
                "partner": edge.get("preferredName_B"),
                "partner_string_id": edge.get("stringId_B"),
                "confidence": round(edge.get("score", 0) / 1000, 3),
                "evidence": {
                    "experimental": edge.get("escore"),
                    "database": edge.get("dscore"),
                    "textmining": edge.get("tscore"),
                    "coexpression": edge.get("ascore"),
                },
            }
        )
    return sorted(interactions, key=lambda x: x["confidence"], reverse=True)


async def top_interactors(identifier: str, species: int = 9606, n: int = 5) -> list[dict[str, Any]]:
    interactions = await get_interactions(identifier, species=species, limit=n, min_score=400)
    return interactions[:n]
