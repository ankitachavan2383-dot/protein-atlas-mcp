# Protein Research MCP Server

**Ask an AI assistant about a protein and get answers backed by real scientific databases.**

This project is a [Model Context Protocol](https://modelcontextprotocol.io) (MCP) server that connects AI clients such as Claude Desktop, Claude Code, and Cursor to the major public bioinformatics resources. Instead of relying on what a model remembers about *TP53* or *EGFR*, the assistant can look up live data from UniProt, AlphaFold, PDB, InterPro, STRING, Reactome, Open Targets, ClinVar, and PubMed.

No API keys are needed. Everything works out of the box.

---

## What can you do with it?

Once connected, you can ask your AI assistant things like:

- "Find the UniProt entry for BRCA1 and give me its sequence length and molecular weight."
- "What is the AlphaFold confidence for EGFR? Are there experimental PDB structures?"
- "Which proteins interact most strongly with KRAS?"
- "What pathways is APOE involved in, and which diseases is it linked to?"
- "Show me the latest papers on PINK1."
- "Generate a full report on TP53."

---

## Capabilities

| Area | Data source | Examples |
|---|---|---|
| **Search** | UniProt | By gene, protein name, accession, or keyword |
| **Sequence analysis** | UniProt + BioPython | Molecular weight, pI, GRAVY, composition, motif search |
| **Structure** | AlphaFold, RCSB PDB | Predicted models, pLDDT confidence, PDB metadata, ligands, file download |
| **Domains** | InterPro | Pfam, SMART, CDD, integrated InterPro annotations |
| **Interactions** | STRING | Partners, confidence scores, evidence breakdown, networks |
| **Pathways** | Reactome | Pathway membership and descriptions |
| **Diseases** | Open Targets, ClinVar | Association scores, cancer filter, clinical variants |
| **Literature** | PubMed, Europe PMC | Search, latest papers, reviews, clinical trials |
| **Reports** | All of the above | One-call report in Markdown, JSON, or HTML |

The `generate_protein_report` tool queries every source concurrently and assembles a single report. If one upstream API is down, only that section is left empty.

---

## Getting started

### 1. Install

```bash
git clone <your-repo-url>
cd protein-research-mcp
uv sync            # or: pip install -r requirements.txt
```

Requires Python 3.10+.

### 2. Run

```bash
uv run server.py
# or
python server.py
```

### 3. Connect a client

Example for Claude Desktop (`claude_desktop_config.json`):

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

Restart the client and the tools will appear.

### 4. Configure (optional)

Create a `.env` file to override defaults:

| Variable | Purpose | Default |
|---|---|---|
| `NCBI_EMAIL` | Identifies you to NCBI (recommended) | `anonymous@example.com` |
| `NCBI_API_KEY` | Higher NCBI rate limits | none |
| `STRING_CALLER_IDENTITY` | Identifies you to STRING | `protein-research-mcp` |
| `TIMEOUT` | HTTP timeout in seconds | `15` |
| `CACHE_DIR` | Disk cache location | `.cache/` in project |
| `LOG_LEVEL` | Logging verbosity | `INFO` |

---

## How it's built

The code is split into three layers so each part is easy to test and reuse:

```
tools/      MCP-facing functions. Validate input, call services, shape output.
services/   One module per external API. Handles URLs, requests, and parsing.
utils/      Pure logic: caching, validation, parsers, sequence math, formatters.
```

Supporting files: `server.py` (entry point), `mcp_app.py` (shared FastMCP instance), `config.py` (settings and base URLs).

Key design choices:

- **Concurrency:** the report generator fans out to eight services with `asyncio.gather()`.
- **Caching:** an in-memory TTL cache plus an optional on-disk JSON cache (UniProt 24h, AlphaFold/PDB 30 days, PubMed 6h, others 1h).
- **Resilience:** HTTP calls retry on transient failures. Tools return `{"error": "..."}` instead of raising, so the AI gets a readable message, not a stack trace.

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for details.

---

## Testing

```bash
pip install -r requirements-dev.txt
pytest
```

The current tests cover the pure sequence utilities and need no network access.

---

## Project status

**Working:** UniProt, AlphaFold, PDB, InterPro, STRING, Reactome, Open Targets, ClinVar, PubMed, Europe PMC, local sequence analysis, and the report generator.

**Stubbed (return a clear "not implemented" note):**

- `kegg_pathways`: needs a UniProt-to-KEGG ID mapping step
- `find_active_sites`: needs UniProt feature annotations or geometric analysis
- `compare_structures`: needs structural alignment (Superimposer, TM-align, or Foldseek)
- `summarize_paper`: needs an LLM call

`find_binding_sites` currently returns the bound-ligand list as a proxy.

## Roadmap

- Protein embeddings (ESM2 / ProtT5) for similarity search
- Local structure prediction for proteins missing from AlphaFold DB
- Foldseek / TM-align structure comparison
- Protein engineering helpers (ProteinMPNN, stability prediction)
- Interactive 3D viewers (Mol\*, py3Dmol)
- Batch FASTA processing
- LLM-generated, evidence-backed summaries

---

## Data sources and acknowledgements

[UniProt](https://www.uniprot.org) · [AlphaFold DB](https://alphafold.ebi.ac.uk) · [RCSB PDB](https://www.rcsb.org) · [InterPro](https://www.ebi.ac.uk/interpro) · [STRING](https://string-db.org) · [Reactome](https://reactome.org) · [Open Targets](https://platform.opentargets.org) · [ClinVar](https://www.ncbi.nlm.nih.gov/clinvar) · [PubMed](https://pubmed.ncbi.nlm.nih.gov) · [Europe PMC](https://europepmc.org) · [BioPython](https://biopython.org)
