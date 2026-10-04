"""UniProt REST API service — search and entry retrieval. No API key required."""
from __future__ import annotations

from typing import Any

from config import settings
from utils.cache import async_cached
from utils.parser import parse_uniprot_entry, parse_uniprot_search_results

from .http_client import request_json, request_text

SERVICE = "uniprot"


@async_cached("uniprot.search", ttl_seconds=settings.ttl_uniprot_seconds)
async def search(query: str, *, organism_id: int | None = None, limit: int = 10) -> list[dict[str, Any]]:
    """
    Free-text search across UniProtKB (gene name, protein name, or accession).
    `query` is passed through UniProt's Lucene-style query syntax, e.g.
    'gene:TP53 AND organism_id:9606' or a bare 'TP53'.
    """
    full_query = query
    if organism_id and "organism_id:" not in query:
        full_query = f"({query}) AND organism_id:{organism_id}"

    params = {
        "query": full_query,
        "fields": "accession,id,protein_name,gene_names,organism_name,length,sequence,cc_function,reviewed",
        "format": "json",
        "size": limit,
    }
    raw = await request_json(SERVICE, "GET", f"{settings.uniprot_base}/uniprotkb/search", params=params)
    return parse_uniprot_search_results(raw or {})


@async_cached("uniprot.entry", ttl_seconds=settings.ttl_uniprot_seconds)
async def get_entry(accession: str) -> dict[str, Any]:
    """Fetch a single UniProtKB entry by accession (e.g. P04637)."""
    raw = await request_json(
        SERVICE, "GET", f"{settings.uniprot_base}/uniprotkb/{accession}", params={"format": "json"}
    )
    return parse_uniprot_entry(raw)


@async_cached("uniprot.fasta", ttl_seconds=settings.ttl_uniprot_seconds)
async def get_fasta(accession: str) -> str:
    """Fetch the raw FASTA sequence for an accession."""
    return await request_text(
        SERVICE, "GET", f"{settings.uniprot_base}/uniprotkb/{accession}.fasta"
    )


async def search_by_gene(gene_name: str, organism_id: int = 9606, limit: int = 5) -> list[dict[str, Any]]:
    """Convenience wrapper: search by gene symbol, defaulting to human (taxon 9606)."""
    return await search(f"gene:{gene_name}", organism_id=organism_id, limit=limit)
