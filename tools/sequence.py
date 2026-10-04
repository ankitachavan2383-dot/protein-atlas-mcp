"""MCP tools: sequence retrieval and local sequence analysis."""
from __future__ import annotations

from typing import Any

from mcp_app import mcp
from services import uniprot
from services.http_client import NotFoundError, UpstreamAPIError
from utils import sequence_utils
from utils.validators import ValidationError, is_uniprot_accession, validate_protein_sequence


@mcp.tool()
async def get_sequence(accession: str) -> dict[str, Any]:
    """
    Retrieve the amino acid sequence for a UniProt accession.

    Args:
        accession: A UniProt accession number, e.g. 'P04637'.
    """
    accession = accession.strip().upper()
    if not is_uniprot_accession(accession):
        return {"error": f"'{accession}' does not look like a valid UniProt accession."}
    try:
        entry = await uniprot.get_entry(accession)
        return {"accession": accession, "length": entry.get("length"), "sequence": entry.get("sequence")}
    except NotFoundError:
        return {"error": f"No UniProt entry found for accession '{accession}'."}
    except UpstreamAPIError as exc:
        return {"error": str(exc)}


@mcp.tool()
def validate_sequence(sequence: str) -> dict[str, Any]:
    """
    Validate a raw or FASTA-formatted amino acid sequence and report any problems.

    Args:
        sequence: Plain sequence text or a full FASTA block (header line + sequence).
    """
    try:
        cleaned = validate_protein_sequence(sequence)
        return {"valid": True, "length": len(cleaned), "cleaned_sequence": cleaned}
    except ValidationError as exc:
        return {"valid": False, "error": str(exc)}


@mcp.tool()
def sequence_length(sequence: str) -> dict[str, Any]:
    """
    Compute the length of an amino acid sequence.

    Args:
        sequence: Plain sequence text or a full FASTA block.
    """
    try:
        cleaned = validate_protein_sequence(sequence)
        return {"length": sequence_utils.sequence_length(cleaned)}
    except ValidationError as exc:
        return {"error": str(exc)}


@mcp.tool()
def molecular_weight(sequence: str) -> dict[str, Any]:
    """
    Compute the molecular weight (Daltons) of an amino acid sequence.

    Args:
        sequence: Plain sequence text or a full FASTA block.
    """
    try:
        cleaned = validate_protein_sequence(sequence)
        return sequence_utils.molecular_weight(cleaned)
    except ValidationError as exc:
        return {"error": str(exc)}


@mcp.tool()
def amino_acid_composition(sequence: str) -> dict[str, Any]:
    """
    Compute the percentage composition of each amino acid in a sequence.

    Args:
        sequence: Plain sequence text or a full FASTA block.
    """
    try:
        cleaned = validate_protein_sequence(sequence)
        return {"composition_percent": sequence_utils.amino_acid_composition(cleaned)}
    except ValidationError as exc:
        return {"error": str(exc)}


@mcp.tool()
def hydrophobicity(sequence: str) -> dict[str, Any]:
    """
    Compute the GRAVY (grand average of hydropathy) score for a sequence.

    Args:
        sequence: Plain sequence text or a full FASTA block.
    """
    try:
        cleaned = validate_protein_sequence(sequence)
        return sequence_utils.hydrophobicity(cleaned)
    except ValidationError as exc:
        return {"error": str(exc)}


@mcp.tool()
def isoelectric_point(sequence: str) -> dict[str, Any]:
    """
    Estimate the isoelectric point (pI) of a sequence.

    Args:
        sequence: Plain sequence text or a full FASTA block.
    """
    try:
        cleaned = validate_protein_sequence(sequence)
        return sequence_utils.isoelectric_point(cleaned)
    except ValidationError as exc:
        return {"error": str(exc)}


@mcp.tool()
def secondary_structure_prediction(sequence: str) -> dict[str, Any]:
    """
    Estimate helix/turn/sheet propensity fractions from sequence composition
    (a fast heuristic, not a substitute for structure-based prediction).

    Args:
        sequence: Plain sequence text or a full FASTA block.
    """
    try:
        cleaned = validate_protein_sequence(sequence)
        return sequence_utils.secondary_structure_prediction(cleaned)
    except ValidationError as exc:
        return {"error": str(exc)}


@mcp.tool()
def motif_search(sequence: str, motif_regex: str) -> dict[str, Any]:
    """
    Search a sequence for regex-style motifs, e.g. 'N[^P][ST][^P]' for the
    N-glycosylation sequon.

    Args:
        sequence: Plain sequence text or a full FASTA block.
        motif_regex: A Python regular expression to match against the sequence.
    """
    try:
        cleaned = validate_protein_sequence(sequence)
        matches = sequence_utils.motif_search(cleaned, motif_regex)
        return {"motif": motif_regex, "match_count": len(matches), "matches": matches}
    except (ValidationError, ValueError) as exc:
        return {"error": str(exc)}
