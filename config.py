"""
Central configuration for the Protein Research MCP Server.

Everything here has a sane, key-free default. Set values in a `.env` file
(see .env.example) to raise rate limits or identify yourself to NCBI/STRING.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


@dataclass(frozen=True)
class Settings:
    # Identity / etiquette headers for public APIs
    ncbi_email: str = field(default_factory=lambda: _env("NCBI_EMAIL", "anonymous@example.com"))
    ncbi_api_key: str = field(default_factory=lambda: _env("NCBI_API_KEY", ""))
    string_caller_identity: str = field(
        default_factory=lambda: _env("STRING_CALLER_IDENTITY", "protein-research-mcp")
    )

    # Networking
    timeout_seconds: float = field(default_factory=lambda: float(_env("TIMEOUT", "15")))
    user_agent: str = "protein-research-mcp/0.1 (+https://github.com/yourname/protein-research-mcp)"

    # Caching
    # Anchored to this project directory (not the process's current working
    # directory) because MCP clients like Claude Desktop often launch the
    # server with an unpredictable cwd - a relative ".cache" path can end up
    # pointing somewhere without write permission (observed on Windows).
    cache_dir: Path = field(
        default_factory=lambda: Path(_env("CACHE_DIR", str(Path(__file__).resolve().parent / ".cache")))
    )
    ttl_uniprot_seconds: int = 24 * 60 * 60
    ttl_alphafold_seconds: int = 30 * 24 * 60 * 60
    ttl_pdb_seconds: int = 30 * 24 * 60 * 60
    ttl_pubmed_seconds: int = 6 * 60 * 60
    ttl_default_seconds: int = 60 * 60

    # Logging
    log_level: str = field(default_factory=lambda: _env("LOG_LEVEL", "INFO"))

    # Base URLs (kept here, not scattered in services, so endpoints are easy to audit/update)
    uniprot_base: str = "https://rest.uniprot.org"
    alphafold_base: str = "https://alphafold.ebi.ac.uk/api"
    alphafold_files_base: str = "https://alphafold.ebi.ac.uk/files"
    pdb_search_base: str = "https://search.rcsb.org/rcsbsearch/v2/query"
    pdb_data_base: str = "https://data.rcsb.org/rest/v1/core"
    pdb_files_base: str = "https://files.rcsb.org/download"
    interpro_base: str = "https://www.ebi.ac.uk/interpro/api"
    string_base: str = "https://string-db.org/api"
    reactome_base: str = "https://reactome.org/ContentService"
    opentargets_base: str = "https://api.platform.opentargets.org/api/v4/graphql"
    clinvar_eutils_base: str = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    pubmed_eutils_base: str = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    europepmc_base: str = "https://www.ebi.ac.uk/europepmc/webservices/rest"


settings = Settings()


def configure_logging() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )


configure_logging()
log = logging.getLogger("protein_mcp")
