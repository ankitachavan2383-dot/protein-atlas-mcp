"""Input validation helpers shared across tools/services."""
from __future__ import annotations

import re

_UNIPROT_ACCESSION_RE = re.compile(
    r"^[OPQ][0-9][A-Z0-9]{3}[0-9]$|^[A-NR-Z][0-9]([A-Z][A-Z0-9]{2}[0-9]){1,2}$"
)
_PDB_ID_RE = re.compile(r"^[0-9][A-Za-z0-9]{3}$")
_VALID_AA = set("ACDEFGHIKLMNPQRSTVWYXBZJUO*")  # includes ambiguity/rare codes + stop


class ValidationError(ValueError):
    """Raised when user-supplied biological identifiers/sequences are malformed."""


def is_uniprot_accession(value: str) -> bool:
    return bool(_UNIPROT_ACCESSION_RE.match(value.strip().upper()))


def is_pdb_id(value: str) -> bool:
    return bool(_PDB_ID_RE.match(value.strip()))


def validate_protein_sequence(sequence: str) -> str:
    """
    Validate (and clean) a raw or FASTA-formatted amino acid sequence.
    Returns the cleaned, uppercase, whitespace-free sequence.
    Raises ValidationError with a human-readable reason on failure.
    """
    if not sequence or not sequence.strip():
        raise ValidationError("Sequence is empty.")

    lines = sequence.strip().splitlines()
    if lines and lines[0].startswith(">"):
        lines = lines[1:]  # strip FASTA header

    cleaned = "".join(line.strip() for line in lines).upper().replace(" ", "")

    if not cleaned:
        raise ValidationError("Sequence contains no residues after removing the FASTA header.")

    invalid_chars = sorted(set(cleaned) - _VALID_AA)
    if invalid_chars:
        raise ValidationError(
            f"Sequence contains invalid amino acid character(s): {', '.join(invalid_chars)}"
        )

    return cleaned


def normalize_identifier(value: str) -> str:
    """Trim/uppercase a gene or accession identifier for consistent cache keys."""
    return value.strip().upper()
