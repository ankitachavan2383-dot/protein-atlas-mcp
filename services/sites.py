"""Binding/active-site data: curated UniProt features + residues contacting PDB ligands."""
from __future__ import annotations

import io
from typing import Any

from config import settings
from utils.cache import async_cached

from . import pdb
from .http_client import request_json

SERVICE = "sites"
SITE_TYPES = {"Active site", "Binding site", "Site", "Metal binding", "DNA binding",
              "Zinc finger", "Motif", "Disulfide bond", "Domain"}
# Common crystallization additives that are not biologically meaningful ligands.
SKIP_LIGANDS = {"GOL", "EDO", "SO4", "PO4", "PEG", "DMS", "ACT", "CL", "NA", "MPD", "FMT", "TRS", "PGE", "BME"}


@async_cached("sites.uniprot", ttl_seconds=settings.ttl_uniprot_seconds)
async def uniprot_sites(accession: str) -> list[dict[str, Any]]:
    """Curated functional-site features (active/binding/metal sites, motifs...) from UniProt."""
    raw = await request_json(
        SERVICE, "GET", f"{settings.uniprot_base}/uniprotkb/{accession}", params={"format": "json"}
    )
    out = []
    for f in (raw or {}).get("features", []):
        if f.get("type") in SITE_TYPES:
            loc = f["location"]
            out.append({
                "type": f["type"],
                "start": loc["start"]["value"],
                "end": loc["end"]["value"],
                "description": f.get("description") or (f.get("ligand") or {}).get("name") or "",
            })
    return out


@async_cached("sites.pockets", ttl_seconds=settings.ttl_pdb_seconds)
async def pdb_pockets(pdb_id: str, cutoff: float = 4.5) -> list[dict[str, Any]]:
    """Residues within `cutoff` angstroms of each bound ligand (geometric, from the PDB file)."""
    from Bio.PDB import NeighborSearch, PDBParser

    text = await pdb.download_pdb_file(pdb_id)
    model = PDBParser(QUIET=True).get_structure(pdb_id, io.StringIO(text))[0]
    search = NeighborSearch(list(model.get_atoms()))

    pockets = []
    for res in model.get_residues():
        if not res.id[0].startswith("H_") or res.get_resname() in SKIP_LIGANDS:
            continue
        near = {}
        for atom in res:
            for n in search.search(atom.coord, cutoff, level="R"):
                if n.id[0] == " ":
                    near[(n.get_parent().id, n.id[1])] = n.get_resname()
        if len(near) >= 3:
            pockets.append({
                "ligand": res.get_resname(),
                "chain": res.get_parent().id,
                "residues": [f"{name}{num}" for (_, num), name in sorted(near.items(), key=lambda kv: kv[0][1])],
            })
    return sorted(pockets, key=lambda p: -len(p["residues"]))[:8]

