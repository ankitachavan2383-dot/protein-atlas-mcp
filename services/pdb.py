"""RCSB PDB search + data + file download service. No API key required."""
from __future__ import annotations

from typing import Any

from config import settings
from utils.cache import async_cached

from .http_client import request_json, request_text

SERVICE = "pdb"


@async_cached("pdb.search_by_uniprot", ttl_seconds=settings.ttl_pdb_seconds)
async def search_by_uniprot(uniprot_accession: str, limit: int = 10) -> list[str]:
    """Find experimentally-determined PDB structures for a given UniProt accession."""
    query = {
        "query": {
            "type": "terminal",
            "service": "text",
            "parameters": {
                "attribute": "rcsb_polymer_entity_container_identifiers.reference_sequence_identifiers.database_accession",
                "operator": "exact_match",
                "value": uniprot_accession,
            },
        },
        "return_type": "entry",
        "request_options": {"paginate": {"start": 0, "rows": limit}},
    }
    raw = await request_json(SERVICE, "POST", settings.pdb_search_base, json_body=query)
    if not raw:
        return []
    return [hit["identifier"] for hit in raw.get("result_set", [])]


@async_cached("pdb.entry", ttl_seconds=settings.ttl_pdb_seconds)
async def get_entry(pdb_id: str) -> dict[str, Any]:
    """Fetch summary metadata (title, method, resolution, organism) for a PDB entry."""
    raw = await request_json(SERVICE, "GET", f"{settings.pdb_data_base}/entry/{pdb_id.upper()}")
    struct = raw.get("struct", {}) or {}
    exptl = raw.get("exptl", [{}])
    resolution = (raw.get("rcsb_entry_info", {}) or {}).get("resolution_combined")
    return {
        "pdb_id": pdb_id.upper(),
        "title": struct.get("title"),
        "experimental_method": exptl[0].get("method") if exptl else None,
        "resolution_angstrom": resolution[0] if resolution else None,
        "deposit_date": (raw.get("rcsb_accession_info", {}) or {}).get("deposit_date"),
    }


async def download_pdb_file(pdb_id: str) -> str:
    """Download the raw legacy PDB-format coordinate file as text."""
    return await request_text(SERVICE, "GET", f"{settings.pdb_files_base}/{pdb_id.upper()}.pdb")


async def download_cif_file(pdb_id: str) -> str:
    """Download the raw mmCIF-format coordinate file as text."""
    return await request_text(SERVICE, "GET", f"{settings.pdb_files_base}/{pdb_id.upper()}.cif")


@async_cached("pdb.ligands", ttl_seconds=settings.ttl_pdb_seconds)
async def get_ligands(pdb_id: str) -> list[dict[str, Any]]:
    """List bound heteroatom/ligand components (excludes water) for a PDB entry."""
    raw = await request_json(SERVICE, "GET", f"{settings.pdb_data_base}/entry/{pdb_id.upper()}")
    ligands = []
    for comp_id in (raw.get("rcsb_entry_info", {}) or {}).get("nonpolymer_bound_components", []) or []:
        if comp_id == "HOH":
            continue
        ligands.append({"component_id": comp_id})
    return ligands
