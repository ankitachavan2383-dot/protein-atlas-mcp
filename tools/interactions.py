"""MCP tools: protein-protein interaction networks via STRING."""
from __future__ import annotations

from typing import Any

from mcp_app import mcp
from services import stringdb
from services.http_client import NotFoundError, UpstreamAPIError


@mcp.tool()
async def get_interactions(
    identifier: str, species: int = 9606, limit: int = 20, min_confidence: float = 0.4
) -> dict[str, Any]:
    """
    Get protein-protein interaction partners from STRING.

    Args:
        identifier: Gene symbol or protein name, e.g. 'KRAS'.
        species: NCBI taxonomy ID (default 9606 = human).
        limit: Max number of partners to return.
        min_confidence: Minimum STRING confidence score, 0.0-1.0 (0.4 = medium confidence).
    """
    try:
        interactions = await stringdb.get_interactions(
            identifier, species=species, limit=limit, min_score=int(min_confidence * 1000)
        )
        return {"identifier": identifier, "partner_count": len(interactions), "interactions": interactions}
    except NotFoundError:
        return {"identifier": identifier, "partner_count": 0, "interactions": []}
    except UpstreamAPIError as exc:
        return {"error": str(exc)}


@mcp.tool()
async def top_interactors(identifier: str, species: int = 9606, n: int = 5) -> dict[str, Any]:
    """
    Get the top N highest-confidence interaction partners for a protein.

    Args:
        identifier: Gene symbol or protein name.
        species: NCBI taxonomy ID (default 9606 = human).
        n: Number of top partners to return.
    """
    try:
        partners = await stringdb.top_interactors(identifier, species=species, n=n)
        return {"identifier": identifier, "top_partners": partners}
    except NotFoundError:
        return {"identifier": identifier, "top_partners": []}
    except UpstreamAPIError as exc:
        return {"error": str(exc)}


@mcp.tool()
async def interaction_network(identifier: str, species: int = 9606, limit: int = 30) -> dict[str, Any]:
    """
    Get a broader interaction network (more partners, lower confidence floor)
    suitable for network visualization.

    Args:
        identifier: Gene symbol or protein name.
        species: NCBI taxonomy ID.
        limit: Max number of edges to return.
    """
    try:
        interactions = await stringdb.get_interactions(identifier, species=species, limit=limit, min_score=150)
        nodes = sorted({identifier.upper()} | {i["partner"] for i in interactions if i.get("partner")})
        edges = [{"source": identifier.upper(), "target": i["partner"], "weight": i["confidence"]} for i in interactions]
        return {"nodes": nodes, "edges": edges}
    except NotFoundError:
        return {"nodes": [identifier.upper()], "edges": []}
    except UpstreamAPIError as exc:
        return {"error": str(exc)}


@mcp.tool()
async def interaction_confidence(identifier: str, partner: str, species: int = 9606) -> dict[str, Any]:
    """
    Look up the STRING confidence score for a specific pair of proteins.

    Args:
        identifier: First gene/protein symbol.
        partner: Second gene/protein symbol to check the interaction confidence with.
        species: NCBI taxonomy ID.
    """
    try:
        interactions = await stringdb.get_interactions(identifier, species=species, limit=200, min_score=0)
        match = next((i for i in interactions if i["partner"].upper() == partner.upper()), None)
        if not match:
            return {"identifier": identifier, "partner": partner, "found": False}
        return {"identifier": identifier, "partner": partner, "found": True, **match}
    except NotFoundError:
        return {"identifier": identifier, "partner": partner, "found": False}
    except UpstreamAPIError as exc:
        return {"error": str(exc)}


@mcp.tool()
async def interaction_sources(identifier: str, species: int = 9606, limit: int = 20) -> dict[str, Any]:
    """
    Break down interaction evidence by source type (experimental, database,
    text-mining, co-expression) for each partner, per STRING's sub-scores.

    Args:
        identifier: Gene symbol or protein name.
        species: NCBI taxonomy ID.
        limit: Max number of partners to return.
    """
    try:
        interactions = await stringdb.get_interactions(identifier, species=species, limit=limit, min_score=400)
        return {
            "identifier": identifier,
            "evidence_breakdown": [
                {"partner": i["partner"], "confidence": i["confidence"], "evidence": i["evidence"]}
                for i in interactions
            ],
        }
    except NotFoundError:
        return {"identifier": identifier, "evidence_breakdown": []}
    except UpstreamAPIError as exc:
        return {"error": str(exc)}
