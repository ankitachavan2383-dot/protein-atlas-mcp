"""MCP tools: protein domain/family annotations via InterPro."""
from __future__ import annotations

from typing import Any

from mcp_app import mcp
from services import interpro
from services.http_client import NotFoundError, UpstreamAPIError
from utils.validators import is_uniprot_accession


@mcp.tool()
async def get_domains(uniprot_accession: str) -> dict[str, Any]:
    """
    Get all InterPro-integrated domain/family annotations for a protein
    (aggregates Pfam, SMART, PROSITE, CDD, and other member databases).

    Args:
        uniprot_accession: UniProt accession, e.g. 'P04637'.
    """
    accession = uniprot_accession.strip().upper()
    if not is_uniprot_accession(accession):
        return {"error": f"'{accession}' does not look like a valid UniProt accession."}
    try:
        domains = await interpro.get_domains(accession)
        return {"accession": accession, "domain_count": len(domains), "domains": domains}
    except NotFoundError:
        return {"accession": accession, "domain_count": 0, "domains": []}
    except UpstreamAPIError as exc:
        return {"error": str(exc)}


@mcp.tool()
async def get_interpro(uniprot_accession: str) -> dict[str, Any]:
    """
    Alias for get_domains - InterPro's integrated view across all member databases.

    Args:
        uniprot_accession: UniProt accession.
    """
    return await get_domains(uniprot_accession)


@mcp.tool()
async def get_pfam(uniprot_accession: str) -> dict[str, Any]:
    """
    Get Pfam-specific domain annotations for a protein.

    Args:
        uniprot_accession: UniProt accession, e.g. 'P04637'.
    """
    accession = uniprot_accession.strip().upper()
    if not is_uniprot_accession(accession):
        return {"error": f"'{accession}' does not look like a valid UniProt accession."}
    try:
        domains = await interpro.get_pfam(accession)
        return {"accession": accession, "domain_count": len(domains), "domains": domains}
    except NotFoundError:
        return {"accession": accession, "domain_count": 0, "domains": []}
    except UpstreamAPIError as exc:
        return {"error": str(exc)}


@mcp.tool()
async def get_smart(uniprot_accession: str) -> dict[str, Any]:
    """
    Get SMART-specific domain annotations for a protein.

    Args:
        uniprot_accession: UniProt accession.
    """
    accession = uniprot_accession.strip().upper()
    if not is_uniprot_accession(accession):
        return {"error": f"'{accession}' does not look like a valid UniProt accession."}
    try:
        domains = await interpro.get_smart(accession)
        return {"accession": accession, "domain_count": len(domains), "domains": domains}
    except NotFoundError:
        return {"accession": accession, "domain_count": 0, "domains": []}
    except UpstreamAPIError as exc:
        return {"error": str(exc)}


@mcp.tool()
async def list_conserved_domains(uniprot_accession: str) -> dict[str, Any]:
    """
    List conserved domains from the CDD (Conserved Domain Database) member database.

    Args:
        uniprot_accession: UniProt accession.
    """
    accession = uniprot_accession.strip().upper()
    if not is_uniprot_accession(accession):
        return {"error": f"'{accession}' does not look like a valid UniProt accession."}
    try:
        domains = await interpro.get_domains(accession, member_db="cdd")
        return {"accession": accession, "domain_count": len(domains), "domains": domains}
    except NotFoundError:
        return {"accession": accession, "domain_count": 0, "domains": []}
    except UpstreamAPIError as exc:
        return {"error": str(exc)}
