"""Open Targets Platform GraphQL API — gene/target-disease association scores. No API key required."""
from __future__ import annotations

from typing import Any

from config import settings
from utils.cache import async_cached

from .http_client import request_json

SERVICE = "opentargets"

_TARGET_ID_QUERY = """
query TargetSearch($q: String!) {
  search(queryString: $q, entityNames: ["target"], page: {size: 1, index: 0}) {
    hits { id name }
  }
}
"""

_ASSOCIATIONS_QUERY = """
query TargetDiseases($ensemblId: String!, $size: Int!) {
  target(ensemblId: $ensemblId) {
    id
    approvedSymbol
    associatedDiseases(page: {size: $size, index: 0}) {
      rows {
        score
        disease { id name }
      }
    }
  }
}
"""


async def _resolve_ensembl_id(gene_symbol: str) -> str | None:
    raw = await request_json(
        SERVICE, "POST", settings.opentargets_base,
        json_body={"query": _TARGET_ID_QUERY, "variables": {"q": gene_symbol}},
    )
    hits = ((raw or {}).get("data", {}).get("search", {}) or {}).get("hits", [])
    return hits[0]["id"] if hits else None


@async_cached("opentargets.diseases", ttl_seconds=settings.ttl_default_seconds)
async def get_disease_associations(gene_symbol: str, limit: int = 15) -> list[dict[str, Any]]:
    """
    Fetch gene-disease association scores (0-1, Open Targets' aggregated
    evidence score) for a gene symbol, e.g. 'BRCA1'.
    """
    ensembl_id = await _resolve_ensembl_id(gene_symbol)
    if not ensembl_id:
        return []

    raw = await request_json(
        SERVICE, "POST", settings.opentargets_base,
        json_body={"query": _ASSOCIATIONS_QUERY, "variables": {"ensemblId": ensembl_id, "size": limit}},
    )
    target = ((raw or {}).get("data", {}) or {}).get("target") or {}
    rows = (target.get("associatedDiseases", {}) or {}).get("rows", [])
    return [
        {
            "disease_id": row["disease"]["id"],
            "disease_name": row["disease"]["name"],
            "association_score": round(row["score"], 4),
        }
        for row in rows
    ]


async def associated_cancers(gene_symbol: str, limit: int = 30) -> list[dict[str, Any]]:
    """Filter disease associations down to entries whose name suggests a cancer/neoplasm."""
    all_diseases = await get_disease_associations(gene_symbol, limit=limit)
    cancer_keywords = ("cancer", "carcinoma", "tumor", "tumour", "neoplasm", "sarcoma", "leukemia", "lymphoma")
    return [d for d in all_diseases if any(k in d["disease_name"].lower() for k in cancer_keywords)]
