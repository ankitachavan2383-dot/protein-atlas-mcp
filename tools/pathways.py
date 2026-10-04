"""MCP tools: biological pathway lookups via Reactome (KEGG stubbed for now)."""
from __future__ import annotations

from typing import Any

from mcp_app import mcp
from services import reactome
from services.http_client import NotFoundError, UpstreamAPIError
from utils.validators import is_uniprot_accession


@mcp.tool()
async def get_pathways(uniprot_accession: str, species: str = "Homo sapiens") -> dict[str, Any]:
    """
    Get all biological pathways a protein participates in (currently Reactome only).

    Args:
        uniprot_accession: UniProt accession, e.g. 'P38398' (BRCA1).
        species: Full species name as Reactome expects it, e.g. 'Homo sapiens'.
    """
    accession = uniprot_accession.strip().upper()
    if not is_uniprot_accession(accession):
        return {"error": f"'{accession}' does not look like a valid UniProt accession."}
    try:
        pathways = await reactome.get_pathways(accession, species=species)
        return {"accession": accession, "pathway_count": len(pathways), "pathways": pathways}
    except NotFoundError:
        return {"accession": accession, "pathway_count": 0, "pathways": []}
    except UpstreamAPIError as exc:
        return {"error": str(exc)}


@mcp.tool()
async def reactome_pathways(uniprot_accession: str, species: str = "Homo sapiens") -> dict[str, Any]:
    """Alias for get_pathways, explicit about the Reactome source."""
    return await get_pathways(uniprot_accession, species=species)


@mcp.tool()
def kegg_pathways(uniprot_accession: str) -> dict[str, Any]:
    """
    NOT YET IMPLEMENTED. KEGG's REST API requires a KEGG gene/pathway ID
    rather than a UniProt accession, so this needs an ID-mapping step
    (via KEGG's conv/ endpoint or UniProt's cross-references) before it can
    be wired up the same way Reactome is.

    Args:
        uniprot_accession: UniProt accession.
    """
    return {
        "implemented": False,
        "note": (
            "Add services/kegg.py: first call https://rest.kegg.jp/conv/genes/uniprot:<accession> "
            "to resolve the KEGG gene ID, then https://rest.kegg.jp/link/pathway/<kegg_gene_id>."
        ),
    }


@mcp.tool()
async def pathway_summary(pathway_id: str) -> dict[str, Any]:
    """
    Get a text description for a single Reactome pathway.

    Args:
        pathway_id: A Reactome stable ID, e.g. 'R-HSA-73894'.
    """
    try:
        summary = await reactome.pathway_summary(pathway_id)
        if not summary:
            return {"error": f"No Reactome pathway found for '{pathway_id}'."}
        return summary
    except NotFoundError:
        return {"error": f"No Reactome pathway found for '{pathway_id}'."}
    except UpstreamAPIError as exc:
        return {"error": str(exc)}
