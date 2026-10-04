"""MCP tool: comprehensive protein report, fanning out to every service concurrently."""
from __future__ import annotations

import asyncio
from typing import Any, Literal

from mcp_app import mcp
from services import alphafold, clinvar, interpro, opentargets, pdb, pubmed, reactome, stringdb, uniprot
from services.http_client import UpstreamAPIError
from utils.formatter import report_to_html, report_to_json, report_to_markdown


async def _safe(coro, default: Any):
    """Run a service call and swallow upstream errors so one dead API doesn't kill the whole report."""
    try:
        return await coro
    except UpstreamAPIError:
        return default
    except Exception:  # noqa: BLE001 - report generation must never hard-fail on one section
        return default


@mcp.tool()
async def generate_protein_report(
    identifier: str,
    is_uniprot_accession: bool = False,
    format: Literal["markdown", "json", "html"] = "markdown",
) -> dict[str, Any]:
    """
    Generate a comprehensive protein report combining basic info, sequence
    stats, domains, structure, interactions, pathways, disease associations,
    and recent publications. All data sources are fetched concurrently.

    Args:
        identifier: A gene symbol (e.g. 'APOE') or UniProt accession.
        is_uniprot_accession: Set True if `identifier` is already a UniProt accession
            (skips the gene->accession search step).
        format: Output format - 'markdown', 'json', or 'html'.
    """
    if is_uniprot_accession:
        accession = identifier.strip().upper()
    else:
        hits = await _safe(uniprot.search_by_gene(identifier, limit=1), [])
        if not hits:
            return {"error": f"Could not resolve '{identifier}' to a UniProt accession."}
        accession = hits[0]["accession"]

    entry = await _safe(uniprot.get_entry(accession), {})
    if not entry:
        return {"error": f"Could not fetch UniProt entry for '{accession}'."}

    gene_symbol = (entry.get("gene_names") or [identifier])[0]

    # Fan out to every remaining data source concurrently - this is the
    # asyncio.gather() pattern called for in the project spec.
    (
        domains,
        af_structure,
        pdb_ids,
        interactions,
        pathways,
        diseases,
        variants,
        papers,
    ) = await asyncio.gather(
        _safe(interpro.get_domains(accession), []),
        _safe(alphafold.get_prediction(accession), {}),
        _safe(pdb.search_by_uniprot(accession, limit=3), []),
        _safe(stringdb.get_interactions(gene_symbol, limit=10), []),
        _safe(reactome.get_pathways(accession), []),
        _safe(opentargets.get_disease_associations(gene_symbol, limit=10), []),
        _safe(clinvar.get_variants(gene_symbol, limit=5), []),
        _safe(pubmed.latest_papers(gene_symbol, limit=5), []),
    )

    pdb_entry = {}
    if pdb_ids:
        pdb_entry = await _safe(pdb.get_entry(pdb_ids[0]), {})

    structure_section = {
        "alphafold_model_id": af_structure.get("model_id"),
        "alphafold_cif_url": af_structure.get("cif_url"),
        "experimental_pdb_ids": pdb_ids,
        "primary_pdb_title": pdb_entry.get("title"),
        "primary_pdb_method": pdb_entry.get("experimental_method"),
        "primary_pdb_resolution_angstrom": pdb_entry.get("resolution_angstrom"),
    }

    summary_parts = [
        f"{entry.get('protein_name') or gene_symbol} ({accession}) is a protein from "
        f"{entry.get('organism', 'an unspecified organism')}, {entry.get('length', '?')} residues long."
    ]
    if domains:
        summary_parts.append(f"It has {len(domains)} annotated domain/family feature(s).")
    if interactions:
        summary_parts.append(f"It interacts with {len(interactions)} partner protein(s) in STRING.")
    if pathways:
        summary_parts.append(f"It participates in {len(pathways)} Reactome pathway(s).")
    if diseases:
        top = diseases[0]["disease_name"]
        summary_parts.append(f"Its strongest disease association is with {top}.")

    report = {
        "basic_info": {
            "query": identifier,
            "accession": accession,
            "protein_name": entry.get("protein_name"),
            "gene_names": entry.get("gene_names"),
            "organism": entry.get("organism"),
            "reviewed": entry.get("reviewed"),
            "function": entry.get("function"),
        },
        "sequence": {"length": entry.get("length"), "sequence": entry.get("sequence")},
        "domains": domains,
        "structure": structure_section,
        "interactions": interactions,
        "pathways": pathways,
        "diseases": diseases,
        "clinvar_variants": variants,
        "publications": papers,
        "summary": " ".join(summary_parts),
    }

    if format == "json":
        return {"format": "json", "accession": accession, "content": report_to_json(report)}
    if format == "html":
        return {"format": "html", "accession": accession, "content": report_to_html(report)}
    return {"format": "markdown", "accession": accession, "content": report_to_markdown(report)}
