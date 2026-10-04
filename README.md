# Protein Research MCP Server

An MCP server that gives AI agents (Claude, Cursor, etc.) tools to research
proteins: search UniProt, pull sequences and run local sequence analysis,
fetch AlphaFold/PDB structures, look up domains, interactions, pathways,
disease associations, and literature — and generate a combined report.

All data sources are free, public, key-free APIs. No signup required to get
started; see [Configuration](#configuration) if you want to raise NCBI's
rate limit.

## Quick start

```bash
# with uv (recommended)
uv venv
uv pip install -r requirements.txt
uv run server.py

# or with plain pip
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python server.py
```

The server speaks MCP over stdio. Point a client at it — see below.

## Connect it to Claude Desktop / Claude Code

Add to your MCP client config (e.g. `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "protein-research": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/protein-research-mcp", "run", "server.py"]
    }
  }
}
```

Or without uv:

```json
{
  "mcpServers": {
    "protein-research": {
      "command": "/absolute/path/to/protein-research-mcp/.venv/bin/python",
      "args": ["/absolute/path/to/protein-research-mcp/server.py"]
    }
  }
}
```

## Configuration

Copy `.env.example` to `.env`. Every value has a working default — the
server runs fully with an empty `.env`. The only thing worth setting is
`NCBI_EMAIL` (identifies you to PubMed/ClinVar's E-utilities; raises your
rate limit from 3 to 10 req/s if you also add `NCBI_API_KEY`).

## Example prompts

- "Search for the TP53 protein"
- "Get the AlphaFold structure for EGFR and tell me the confidence"
- "What pathways does BRCA1 participate in?"
- "Find the top interacting proteins for KRAS"
- "Generate a complete report for APOE"
- "Validate this sequence: MEEPQSDPSV... and tell me its molecular weight"

## Tool inventory

| Category | Tools |
|---|---|
| Search | `search_protein`, `search_gene`, `search_uniprot`, `search_by_keyword` |
| Sequence | `get_sequence`, `validate_sequence`, `sequence_length`, `molecular_weight`, `amino_acid_composition`, `hydrophobicity`, `isoelectric_point`, `secondary_structure_prediction`, `motif_search` |
| Structure | `get_alphafold_structure`, `get_pdb_structure`, `download_pdb`, `download_cif`, `get_plddt`, `summarize_structure`, `find_ligands`, `find_binding_sites`, `find_active_sites`*, `compare_structures`* |
| Domains | `get_domains`, `get_interpro`, `get_pfam`, `get_smart`, `list_conserved_domains` |
| Interactions | `get_interactions`, `top_interactors`, `interaction_network`, `interaction_confidence`, `interaction_sources` |
| Pathways | `get_pathways`, `reactome_pathways`, `kegg_pathways`*, `pathway_summary` |
| Diseases | `get_diseases`, `clinvar_variants`, `open_targets`, `gene_disease_score`, `associated_cancers` |
| Literature | `search_pubmed`, `latest_papers`, `protein_reviews`, `clinical_trials`, `search_europepmc`, `summarize_paper`* |
| Reports | `generate_protein_report` |

`*` = stubbed, returns `{"implemented": false, "note": "..."}` explaining
exactly what's needed to finish it. See `docs/ARCHITECTURE.md`.

## Data sources

UniProt · AlphaFold DB · RCSB PDB · InterPro (Pfam/SMART/CDD) · STRING ·
Reactome · Open Targets · ClinVar (NCBI E-utilities) · PubMed (NCBI
E-utilities) · Europe PMC — all free, no API key required.

## Testing

```bash
pip install -r requirements-dev.txt
pytest -v
```

The included tests cover the network-free layer (`utils/`) — sequence math,
validators, and response parsers — so they run offline and fast. Service
calls (`services/*.py`) hit live APIs and are meant to be exercised by
actually running the server against a real MCP client.

## Project layout

See `docs/ARCHITECTURE.md` for the full design writeup (layering rationale,
caching strategy, concurrency pattern, error handling, and the roadmap for
the stubbed tools and future enhancements listed in the original spec).
