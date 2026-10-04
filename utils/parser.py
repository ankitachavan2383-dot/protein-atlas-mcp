"""
Parsers that turn raw API payloads (UniProt JSON, PDB search JSON, NCBI
E-utilities XML, etc.) into the small, flat dicts our tools return.
Keeping this separate from `services/` means a service's job is only
"go get the raw thing"; the shaping logic lives here and is unit-testable
without any network access.
"""
from __future__ import annotations

from typing import Any
from xml.etree import ElementTree


def parse_uniprot_entry(raw: dict[str, Any]) -> dict[str, Any]:
    """Flatten a UniProt REST JSON entry into the fields tools actually need."""
    accession = raw.get("primaryAccession", "")
    protein_desc = raw.get("proteinDescription", {})
    recommended = protein_desc.get("recommendedName", {}) or {}
    full_name = (recommended.get("fullName") or {}).get("value")
    if not full_name:
        alt_names = protein_desc.get("alternativeNames") or []
        full_name = (alt_names[0].get("fullName", {}).get("value") if alt_names else None)

    genes = raw.get("genes") or []
    gene_names = [g["geneName"]["value"] for g in genes if "geneName" in g]

    organism = (raw.get("organism") or {}).get("scientificName")

    sequence_block = raw.get("sequence") or {}

    function_texts = []
    for comment in raw.get("comments", []):
        if comment.get("commentType") == "FUNCTION":
            for text in comment.get("texts", []):
                if text.get("value"):
                    function_texts.append(text["value"])

    return {
        "accession": accession,
        "protein_name": full_name,
        "gene_names": gene_names,
        "organism": organism,
        "length": sequence_block.get("length"),
        "sequence": sequence_block.get("value"),
        "function": " ".join(function_texts) if function_texts else None,
        "reviewed": raw.get("entryType", "").startswith("UniProtKB reviewed"),
    }


def parse_uniprot_search_results(raw: dict[str, Any]) -> list[dict[str, Any]]:
    return [parse_uniprot_entry(entry) for entry in raw.get("results", [])]


def parse_ncbi_esearch_ids(raw: dict[str, Any]) -> list[str]:
    return raw.get("esearchresult", {}).get("idlist", [])


def parse_pubmed_esummary(raw: dict[str, Any]) -> list[dict[str, Any]]:
    result = raw.get("result", {})
    uids = result.get("uids", [])
    papers = []
    for uid in uids:
        item = result.get(uid, {})
        authors = [a.get("name") for a in item.get("authors", []) if a.get("name")]
        papers.append(
            {
                "pmid": uid,
                "title": item.get("title"),
                "authors": authors,
                "journal": item.get("fulljournalname") or item.get("source"),
                "pub_date": item.get("pubdate"),
                "doi": next(
                    (aid["value"] for aid in item.get("articleids", []) if aid.get("idtype") == "doi"),
                    None,
                ),
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{uid}/",
            }
        )
    return papers


def parse_clinvar_esummary(raw: dict[str, Any]) -> list[dict[str, Any]]:
    result = raw.get("result", {})
    uids = result.get("uids", [])
    variants = []
    for uid in uids:
        item = result.get(uid, {})
        germline = item.get("germline_classification", {}) or {}
        variants.append(
            {
                "variation_id": uid,
                "title": item.get("title"),
                "clinical_significance": germline.get("description"),
                "review_status": germline.get("review_status"),
                "conditions": [
                    trait.get("trait_name")
                    for trait in germline.get("trait_set", []) or []
                    if trait.get("trait_name")
                ],
                "url": f"https://www.ncbi.nlm.nih.gov/clinvar/variation/{uid}/",
            }
        )
    return variants


def xml_text(element: ElementTree.Element | None) -> str | None:
    return element.text.strip() if element is not None and element.text else None
