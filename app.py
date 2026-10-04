"""
Web UI backend for the Protein Research project.

Reuses the existing services/ and utils/ layers (no duplicated API logic).
Run:  uvicorn app:app --reload      then open http://127.0.0.1:8000
"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from pydantic import BaseModel

from services import alphafold, pdb, uniprot
from services import sites as site_svc
from services.http_client import UpstreamAPIError, request_text
from tools.reports import generate_protein_report
from utils import sequence_utils
from utils.validators import ValidationError, is_uniprot_accession, validate_protein_sequence

app = FastAPI(title="Protein Research UI")
INDEX = Path(__file__).resolve().parent / "static" / "index.html"


class SeqIn(BaseModel):
    sequence: str


def _err(msg: str, code: int = 400) -> JSONResponse:
    return JSONResponse({"error": msg}, status_code=code)


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(INDEX)


@app.get("/api/search")
async def search(q: str):
    try:
        hits = await uniprot.search(q.strip(), organism_id=9606, limit=8)
    except UpstreamAPIError as exc:
        return _err(str(exc), 502)
    return [{k: h.get(k) for k in ("accession", "protein_name", "gene_names", "organism")} for h in hits]


@app.get("/api/report")
async def report(q: str):
    q = q.strip()
    if not q:
        return _err("Enter a gene symbol or UniProt accession.")
    res = await generate_protein_report(q, is_uniprot_accession=is_uniprot_accession(q), format="json")
    if "error" in res:
        return _err(res["error"], 404)
    data = json.loads(res["content"])
    seq = (data.get("sequence") or {}).get("sequence")
    data["sequence_stats"] = sequence_utils.full_sequence_stats(seq) if seq else {}
    return data


@app.post("/api/sequence")
async def analyze(body: SeqIn):
    try:
        cleaned = validate_protein_sequence(body.sequence)
    except ValidationError as exc:
        return _err(str(exc))
    return sequence_utils.full_sequence_stats(cleaned)


@app.get("/api/model/{acc}")
async def model(acc: str):
    """Proxy the AlphaFold PDB file (avoids browser CORS issues)."""
    if not is_uniprot_accession(acc):
        return _err("Invalid UniProt accession.")
    try:
        pred = await alphafold.get_prediction(acc)
        return PlainTextResponse(await request_text("alphafold", "GET", pred["pdb_url"]))
    except (UpstreamAPIError, KeyError) as exc:
        return _err(str(exc), 404)


@app.get("/api/sites/{acc}")
async def sites(acc: str):
    """Curated UniProt functional sites + ligand-contact pockets from experimental PDB structures."""
    if not is_uniprot_accession(acc):
        return _err("Invalid UniProt accession.")
    try:
        features = await site_svc.uniprot_sites(acc)
        pockets = []
        for pid in (await pdb.search_by_uniprot(acc, limit=3))[:2]:
            try:
                pockets += [{"pdb_id": pid, **p} for p in await site_svc.pdb_pockets(pid)]
            except UpstreamAPIError:
                continue  # e.g. very large entries with no legacy .pdb file
    except UpstreamAPIError as exc:
        return _err(str(exc), 502)
    return {"features": features, "pockets": pockets}