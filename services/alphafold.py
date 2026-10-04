"""AlphaFold Protein Structure Database service. No API key required."""
from __future__ import annotations

from typing import Any

from config import settings
from utils.cache import async_cached

from .http_client import request_json

SERVICE = "alphafold"


@async_cached("alphafold.prediction", ttl_seconds=settings.ttl_alphafold_seconds)
async def get_prediction(uniprot_accession: str) -> dict[str, Any]:
    """
    Fetch AlphaFold model metadata for a UniProt accession: model version,
    CIF/PDB download URLs, and the per-residue confidence (pLDDT) summary URL.
    """
    raw = await request_json(
        SERVICE, "GET", f"{settings.alphafold_base}/prediction/{uniprot_accession}"
    )
    if not raw:
        return {}
    entry = raw[0]
    return {
        "uniprot_accession": uniprot_accession,
        "model_id": entry.get("entryId"),
        "model_version": entry.get("latestVersion"),
        "sequence_length": entry.get("uniprotEnd"),
        "pdb_url": entry.get("pdbUrl"),
        "cif_url": entry.get("cifUrl"),
        "plddt_png_url": entry.get("paeImageUrl"),
        "pae_doc_url": entry.get("paeDocUrl"),
        "created_date": entry.get("modelCreatedDate"),
    }


def confidence_summary(mean_plddt: float) -> str:
    """Translate a mean pLDDT score into AlphaFold's own confidence bands."""
    if mean_plddt >= 90:
        return "Very high confidence (pLDDT > 90)"
    if mean_plddt >= 70:
        return "Confident (90 > pLDDT > 70)"
    if mean_plddt >= 50:
        return "Low confidence (70 > pLDDT > 50)"
    return "Very low confidence (pLDDT < 50) — likely disordered region"
