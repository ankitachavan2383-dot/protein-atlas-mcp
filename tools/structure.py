"""MCP tools: AlphaFold predicted structures and experimental PDB structures."""
from __future__ import annotations

import io
import statistics
from typing import Any

from mcp_app import mcp
from services import alphafold, pdb
from services.http_client import NotFoundError, UpstreamAPIError
from utils.validators import is_pdb_id, is_uniprot_accession


@mcp.tool()
async def get_alphafold_structure(uniprot_accession: str) -> dict[str, Any]:
    """
    Get the AlphaFold predicted structure for a protein, including download
    links and a confidence summary.

    Args:
        uniprot_accession: UniProt accession, e.g. 'P00533' (EGFR).
    """
    accession = uniprot_accession.strip().upper()
    if not is_uniprot_accession(accession):
        return {"error": f"'{accession}' does not look like a valid UniProt accession."}
    try:
        prediction = await alphafold.get_prediction(accession)
        if not prediction:
            return {"error": f"No AlphaFold model found for '{accession}'."}
        return prediction
    except NotFoundError:
        return {"error": f"No AlphaFold model found for '{accession}'."}
    except UpstreamAPIError as exc:
        return {"error": str(exc)}


@mcp.tool()
async def get_pdb_structure(pdb_id: str) -> dict[str, Any]:
    """
    Get experimental structure metadata (method, resolution, title) for a PDB entry.

    Args:
        pdb_id: A 4-character PDB ID, e.g. '1TUP'.
    """
    pdb_id = pdb_id.strip()
    if not is_pdb_id(pdb_id):
        return {"error": f"'{pdb_id}' does not look like a valid 4-character PDB ID."}
    try:
        return await pdb.get_entry(pdb_id)
    except NotFoundError:
        return {"error": f"No PDB entry found for '{pdb_id}'."}
    except UpstreamAPIError as exc:
        return {"error": str(exc)}


@mcp.tool()
async def download_pdb(pdb_id: str, max_chars: int = 5000) -> dict[str, Any]:
    """
    Download the raw legacy .pdb coordinate file for a structure (truncated
    for display; the full file is what you'd write to disk).

    Args:
        pdb_id: A 4-character PDB ID.
        max_chars: Truncate the returned text to this many characters.
    """
    pdb_id = pdb_id.strip()
    if not is_pdb_id(pdb_id):
        return {"error": f"'{pdb_id}' does not look like a valid 4-character PDB ID."}
    try:
        text = await pdb.download_pdb_file(pdb_id)
        return {
            "pdb_id": pdb_id.upper(),
            "total_chars": len(text),
            "truncated": len(text) > max_chars,
            "content": text[:max_chars],
        }
    except NotFoundError:
        return {"error": f"No PDB file found for '{pdb_id}'."}
    except UpstreamAPIError as exc:
        return {"error": str(exc)}


@mcp.tool()
async def download_cif(pdb_id: str, max_chars: int = 5000) -> dict[str, Any]:
    """
    Download the raw mmCIF coordinate file for a structure (truncated for display).

    Args:
        pdb_id: A 4-character PDB ID.
        max_chars: Truncate the returned text to this many characters.
    """
    pdb_id = pdb_id.strip()
    if not is_pdb_id(pdb_id):
        return {"error": f"'{pdb_id}' does not look like a valid 4-character PDB ID."}
    try:
        text = await pdb.download_cif_file(pdb_id)
        return {
            "pdb_id": pdb_id.upper(),
            "total_chars": len(text),
            "truncated": len(text) > max_chars,
            "content": text[:max_chars],
        }
    except NotFoundError:
        return {"error": f"No CIF file found for '{pdb_id}'."}
    except UpstreamAPIError as exc:
        return {"error": str(exc)}


@mcp.tool()
async def get_plddt(uniprot_accession: str) -> dict[str, Any]:
    """
    Compute the mean per-residue AlphaFold confidence (pLDDT) for a protein by
    downloading its CIF file and reading the confidence values Bio.PDB exposes
    as the B-factor column.

    Args:
        uniprot_accession: UniProt accession, e.g. 'P00533'.
    """
    accession = uniprot_accession.strip().upper()
    if not is_uniprot_accession(accession):
        return {"error": f"'{accession}' does not look like a valid UniProt accession."}
    try:
        prediction = await alphafold.get_prediction(accession)
        if not prediction or not prediction.get("cif_url"):
            return {"error": f"No AlphaFold model found for '{accession}'."}

        from services.http_client import request_text

        cif_text = await request_text("alphafold", "GET", prediction["cif_url"])

        from Bio.PDB.MMCIFParser import MMCIFParser

        parser = MMCIFParser(QUIET=True)
        structure = parser.get_structure(accession, io.StringIO(cif_text))
        plddt_values = [atom.get_bfactor() for atom in structure.get_atoms()]

        if not plddt_values:
            return {"error": "Could not extract confidence values from the CIF file."}

        mean_plddt = round(statistics.mean(plddt_values), 2)
        return {
            "uniprot_accession": accession,
            "mean_plddt": mean_plddt,
            "min_plddt": round(min(plddt_values), 2),
            "max_plddt": round(max(plddt_values), 2),
            "confidence_summary": alphafold.confidence_summary(mean_plddt),
        }
    except (NotFoundError, UpstreamAPIError) as exc:
        return {"error": str(exc)}


@mcp.tool()
async def summarize_structure(pdb_id: str) -> dict[str, Any]:
    """
    Combine PDB entry metadata and bound ligands into one summary.

    Args:
        pdb_id: A 4-character PDB ID.
    """
    pdb_id = pdb_id.strip()
    if not is_pdb_id(pdb_id):
        return {"error": f"'{pdb_id}' does not look like a valid 4-character PDB ID."}
    try:
        entry = await pdb.get_entry(pdb_id)
        ligands = await pdb.get_ligands(pdb_id)
        return {**entry, "bound_ligands": ligands}
    except NotFoundError:
        return {"error": f"No PDB entry found for '{pdb_id}'."}
    except UpstreamAPIError as exc:
        return {"error": str(exc)}


@mcp.tool()
async def find_ligands(pdb_id: str) -> dict[str, Any]:
    """
    List non-water heteroatom/ligand components bound in a PDB structure.

    Args:
        pdb_id: A 4-character PDB ID.
    """
    pdb_id = pdb_id.strip()
    if not is_pdb_id(pdb_id):
        return {"error": f"'{pdb_id}' does not look like a valid 4-character PDB ID."}
    try:
        ligands = await pdb.get_ligands(pdb_id)
        return {"pdb_id": pdb_id.upper(), "ligand_count": len(ligands), "ligands": ligands}
    except NotFoundError:
        return {"error": f"No PDB entry found for '{pdb_id}'."}
    except UpstreamAPIError as exc:
        return {"error": str(exc)}


@mcp.tool()
async def find_binding_sites(pdb_id: str) -> dict[str, Any]:
    """
    Approximate binding sites by returning bound ligand components. For true
    residue-level binding-site geometry (residues within N angstroms of each
    ligand), this needs local structure parsing - see find_active_sites.

    Args:
        pdb_id: A 4-character PDB ID.
    """
    result = await find_ligands(pdb_id)
    if "error" in result:
        return result
    result["note"] = (
        "This lists bound ligands as a proxy for binding sites. Residue-level "
        "pocket geometry is not yet computed - see docs/ARCHITECTURE.md roadmap."
    )
    return result


@mcp.tool()
def find_active_sites(pdb_id: str) -> dict[str, Any]:
    """
    NOT YET IMPLEMENTED. Active-site residue identification requires curated
    annotation (e.g. UniProt 'Active site' features) or local geometric
    analysis of the structure, neither of which is wired up yet.

    Args:
        pdb_id: A 4-character PDB ID.
    """
    return {
        "implemented": False,
        "note": (
            "Use UniProt's feature annotations (comments/features of type 'Active site') "
            "via services.uniprot.get_entry for curated active-site data, or extend this "
            "tool with local structure analysis. Left as a stub intentionally."
        ),
    }


@mcp.tool()
def compare_structures(pdb_id_a: str, pdb_id_b: str) -> dict[str, Any]:
    """
    NOT YET IMPLEMENTED. Structural alignment/RMSD comparison (e.g. via
    Bio.PDB Superimposer, TM-align, or Foldseek) is on the roadmap.

    Args:
        pdb_id_a: First PDB ID.
        pdb_id_b: Second PDB ID.
    """
    return {
        "implemented": False,
        "note": (
            "Planned: download both CIF files, extract CA atoms, align with "
            "Bio.PDB.Superimposer for same-length chains, or shell out to "
            "TM-align/Foldseek for sequence-independent comparison. See "
            "docs/ARCHITECTURE.md future enhancements."
        ),
    }
