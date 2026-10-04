# Architecture

## Layers

```
tools/      MCP-facing functions. Thin: validate input -> call one or more
            services -> shape the output dict. No HTTP calls live here.
services/   One module per external API. Owns the URL, request shape, and
            response parsing for that API. No MCP/tool-decorator code here -
            these are plain async functions you could unit-test or reuse
            in a completely different context (a CLI, a notebook, etc).
utils/      Pure, network-free logic: caching decorator, validators,
            BioPython-backed sequence math, response parsers, report
            formatters. Nothing here imports httpx.
mcp_app.py  The single shared FastMCP() instance, in its own module so
            tools/*.py and server.py don't form an import cycle.
server.py   Imports every tools/* module (for the @mcp.tool() registration
            side effect) and calls mcp.run().
```

Why split `services` from `tools` at all? Two reasons:

1. **Testability.** `utils/sequence_utils.py` and `utils/parser.py` are pure
   functions - the test suite in `tests/` exercises them with zero network
   access. `services/*.py` are the only things that touch httpx, so if you
   want integration tests that hit real APIs, they're easy to isolate and
   mark `@pytest.mark.integration`.
2. **Reuse.** `generate_protein_report` in `tools/reports.py` calls seven
   services directly via `asyncio.gather()` rather than calling other tool
   functions. Tools are the outermost, MCP-specific layer; services are the
   reusable core.

## Caching (`utils/cache.py`)

Two tiers: an in-memory `cachetools.TTLCache` (fast, cleared on restart) and
an optional flat-file JSON cache on disk (survives restarts). The
`@async_cached(namespace, ttl_seconds)` decorator wraps a service function;
the cache key is a hash of the function's arguments. TTLs match the spec:
UniProt 24h, AlphaFold/PDB 30 days, PubMed 6h, everything else 1h by default
(see `config.Settings`).

This is intentionally *not* Redis or SQLite - the spec calls those optional,
and flat JSON files are enough to demonstrate the caching pattern without
adding infrastructure a reviewer has to stand up to run the project.
Swapping in Redis later means changing `_disk_read`/`_disk_write` in
`utils/cache.py` and nothing else.

## Concurrency

`tools/reports.py::generate_protein_report` is the canonical example of the
"parallel API calls" requirement: after resolving the UniProt accession, it
fires eight independent service calls via a single `asyncio.gather()` and
only then assembles the report. Each call is wrapped in `_safe()` so a dead
or slow upstream (say, Open Targets is down) degrades that one section to an
empty list instead of failing the whole report.

## Error handling

`services/http_client.py` defines two exception types:

- `UpstreamAPIError` - network failure, timeout, non-2xx, or bad JSON.
- `NotFoundError(UpstreamAPIError)` - specifically a 404 (bad accession/ID).

Every tool function catches these and returns `{"error": "..."}` rather than
letting an exception propagate to the MCP client - agents calling these
tools get a usable message instead of a stack trace.

## What's fully implemented vs. stubbed

Fully implemented (real API calls, parsed responses, tests where the logic
is network-free):
- UniProt (search, entry, FASTA)
- AlphaFold (prediction metadata, mean pLDDT via CIF parsing)
- RCSB PDB (search by UniProt accession, entry metadata, PDB/CIF download, ligands)
- InterPro (domains, Pfam, SMART, CDD)
- STRING (interactions, confidence breakdown, network edges)
- Reactome (pathways, pathway summary)
- Open Targets (disease association scores, cancer filter)
- ClinVar (variant summaries)
- PubMed / Europe PMC (search, latest papers, reviews, clinical trials)
- Report generator (concurrent fan-out + markdown/json/html rendering)

Deliberately stubbed, with a note explaining exactly what's missing, in the
tool's own docstring/return value:
- `kegg_pathways` - needs a UniProt->KEGG gene ID mapping step first.
- `find_active_sites` - needs curated UniProt feature annotations or local
  geometric analysis; `find_binding_sites` currently proxies this with the
  ligand list.
- `compare_structures` - needs Bio.PDB.Superimposer (same-length chains) or
  a TM-align/Foldseek shell-out (sequence-independent).
- `summarize_paper` - needs an actual LLM call (e.g. to the Anthropic API);
  currently a stub so the tool exists and returns a clear "not implemented" shape.

## Roadmap (from the original spec, unchanged)

- Protein embeddings (ESM2/ProtT5) for similarity search
- Local structure prediction (OpenFold/ColabFold) for proteins missing from AlphaFold DB
- Foldseek/TM-align structure comparison
- ProteinMPNN / stability prediction for protein engineering
- Mol*/py3Dmol interactive 3D viewers
- Batch FASTA processing
- LLM-generated evidence-backed summaries
