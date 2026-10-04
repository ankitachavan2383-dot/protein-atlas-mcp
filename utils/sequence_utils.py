"""
Pure, local sequence-analysis helpers. Nothing in this module makes a
network call - it only computes on a sequence string the caller already has,
using BioPython's ProtParam where possible.
"""
from __future__ import annotations

from typing import Any

from Bio.SeqUtils.ProtParam import ProteinAnalysis

# Residues ProtParam can't score (ambiguity/rare codes); we strip them for the
# physicochemical calculations but report how many were dropped.
_PROTPARAM_UNSUPPORTED = set("XBZJUO*")


def _clean_for_protparam(sequence: str) -> tuple[str, int]:
    dropped = sum(1 for c in sequence if c in _PROTPARAM_UNSUPPORTED)
    clean = "".join(c for c in sequence if c not in _PROTPARAM_UNSUPPORTED)
    return clean, dropped


def sequence_length(sequence: str) -> int:
    return len(sequence)


def amino_acid_composition(sequence: str) -> dict[str, float]:
    length = len(sequence) or 1
    counts: dict[str, int] = {}
    for residue in sequence:
        counts[residue] = counts.get(residue, 0) + 1
    return {residue: round(count / length * 100, 2) for residue, count in sorted(counts.items())}


def molecular_weight(sequence: str) -> dict[str, Any]:
    clean, dropped = _clean_for_protparam(sequence)
    if not clean:
        return {"molecular_weight_da": None, "note": "No standard residues to compute weight from."}
    analysis = ProteinAnalysis(clean)
    result: dict[str, Any] = {"molecular_weight_da": round(analysis.molecular_weight(), 2)}
    if dropped:
        result["note"] = f"{dropped} non-standard residue(s) excluded from calculation."
    return result


def isoelectric_point(sequence: str) -> dict[str, Any]:
    clean, dropped = _clean_for_protparam(sequence)
    if not clean:
        return {"isoelectric_point": None, "note": "No standard residues to compute pI from."}
    analysis = ProteinAnalysis(clean)
    result: dict[str, Any] = {"isoelectric_point": round(analysis.isoelectric_point(), 2)}
    if dropped:
        result["note"] = f"{dropped} non-standard residue(s) excluded from calculation."
    return result


def hydrophobicity(sequence: str) -> dict[str, Any]:
    """Grand average of hydropathy (GRAVY) via Kyte-Doolittle, plus a plain-English read."""
    clean, dropped = _clean_for_protparam(sequence)
    if not clean:
        return {"gravy": None, "note": "No standard residues to compute GRAVY from."}
    analysis = ProteinAnalysis(clean)
    gravy = analysis.gravy()
    interpretation = "hydrophobic" if gravy > 0 else "hydrophilic"
    result: dict[str, Any] = {"gravy": round(gravy, 3), "interpretation": interpretation}
    if dropped:
        result["note"] = f"{dropped} non-standard residue(s) excluded from calculation."
    return result


def secondary_structure_prediction(sequence: str) -> dict[str, Any]:
    """
    Fraction of residues predicted to favor helix / turn / sheet, using
    BioPython's ProtParam propensity tables. This is a fast heuristic
    (not DSSP/PSIPRED-grade) - good enough for a quick composition-based
    estimate and clearly labeled as such.
    """
    clean, dropped = _clean_for_protparam(sequence)
    if not clean:
        return {"helix": None, "turn": None, "sheet": None, "note": "No standard residues to analyze."}
    analysis = ProteinAnalysis(clean)
    helix, turn, sheet = analysis.secondary_structure_fraction()
    result: dict[str, Any] = {
        "helix_fraction": round(helix, 3),
        "turn_fraction": round(turn, 3),
        "sheet_fraction": round(sheet, 3),
        "method": "ProtParam composition-based propensity (heuristic, not structure-based)",
    }
    if dropped:
        result["note"] = f"{dropped} non-standard residue(s) excluded from calculation."
    return result


def motif_search(sequence: str, motif_regex: str) -> list[dict[str, int | str]]:
    """
    Find all (possibly overlapping) matches of a regular-expression motif
    (e.g. PROSITE-style patterns translated to regex, like 'N[^P][ST][^P]'
    for the N-glycosylation sequon) in the sequence.
    """
    import re

    try:
        pattern = re.compile(motif_regex)
    except re.error as exc:
        raise ValueError(f"Invalid motif regex: {exc}") from exc

    matches = []
    for i in range(len(sequence)):
        m = pattern.match(sequence, i)
        if m:
            matches.append({"start": i + 1, "end": m.end(), "match": m.group()})  # 1-indexed
    return matches


def full_sequence_stats(sequence: str) -> dict[str, Any]:
    """Convenience bundle used by the `sequence_length`/report tools."""
    return {
        "length": sequence_length(sequence),
        "molecular_weight": molecular_weight(sequence),
        "isoelectric_point": isoelectric_point(sequence),
        "hydrophobicity": hydrophobicity(sequence),
        "amino_acid_composition": amino_acid_composition(sequence),
    }
