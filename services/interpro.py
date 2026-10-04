"""InterPro API — domain, family, and site annotations (covers Pfam, SMART, etc). No key required."""
from __future__ import annotations

from typing import Any

from config import settings
from utils.cache import async_cached

from .http_client import request_json

SERVICE = "interpro"


@async_cached("interpro.domains", ttl_seconds=settings.ttl_uniprot_seconds)
async def get_domains(uniprot_accession: str, member_db: str | None = None) -> list[dict[str, Any]]:
    """
    Fetch domain/family entries for a UniProt accession.
    `member_db` narrows results to a specific source database: 'pfam', 'smart',
    'prosite', 'cdd', etc. Leave as None to get InterPro's integrated calls
    across all member databases.
    """
    path = f"entry/{member_db}/protein/uniprot/{uniprot_accession}" if member_db else (
        f"entry/interpro/protein/uniprot/{uniprot_accession}"
    )
    raw = await request_json(SERVICE, "GET", f"{settings.interpro_base}/{path}", params={"page_size": 100})
    if not raw:
        return []

    domains = []
    for item in raw.get("results", []):
        metadata = item.get("metadata", {})
        for protein in item.get("proteins", []):
            for loc in protein.get("entry_protein_locations", []) or []:
                for fragment in loc.get("fragments", []) or []:
                    domains.append(
                        {
                            "id": metadata.get("accession"),
                            "name": metadata.get("name"),
                            "type": metadata.get("type"),
                            "source_database": metadata.get("source_database"),
                            "start": fragment.get("start"),
                            "end": fragment.get("end"),
                        }
                    )
    return domains


async def get_pfam(uniprot_accession: str) -> list[dict[str, Any]]:
    return await get_domains(uniprot_accession, member_db="pfam")


async def get_smart(uniprot_accession: str) -> list[dict[str, Any]]:
    return await get_domains(uniprot_accession, member_db="smart")
