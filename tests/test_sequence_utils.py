"""
Unit tests for network-free logic: sequence math, validation, and parsing.
Run with: pytest

These deliberately avoid the network (no httpx calls) so they run fast and
in CI without needing live API access. Service-layer integration tests
would live in tests/test_services_integration.py and be marked to skip in CI.
"""
from __future__ import annotations

import pytest

from utils import sequence_utils
from utils.parser import parse_pubmed_esummary, parse_uniprot_entry
from utils.validators import ValidationError, is_pdb_id, is_uniprot_accession, validate_protein_sequence

TP53_FRAGMENT = "MEEPQSDPSVEPPLSQETFSDLWKLLPENNVLSPLPS"


def test_validate_protein_sequence_strips_fasta_header():
    fasta = f">sp|P04637|P53_HUMAN Cellular tumor antigen p53\n{TP53_FRAGMENT}"
    assert validate_protein_sequence(fasta) == TP53_FRAGMENT


def test_validate_protein_sequence_rejects_invalid_chars():
    with pytest.raises(ValidationError):
        validate_protein_sequence("MEEP123")


def test_validate_protein_sequence_rejects_empty():
    with pytest.raises(ValidationError):
        validate_protein_sequence("   ")


def test_sequence_length():
    assert sequence_utils.sequence_length(TP53_FRAGMENT) == len(TP53_FRAGMENT)


def test_molecular_weight_positive():
    result = sequence_utils.molecular_weight(TP53_FRAGMENT)
    assert result["molecular_weight_da"] > 0


def test_amino_acid_composition_sums_to_100():
    comp = sequence_utils.amino_acid_composition(TP53_FRAGMENT)
    assert pytest.approx(sum(comp.values()), abs=0.5) == 100.0


def test_hydrophobicity_returns_gravy_and_interpretation():
    result = sequence_utils.hydrophobicity(TP53_FRAGMENT)
    assert "gravy" in result and "interpretation" in result


def test_motif_search_finds_glycosylation_sequon():
    # N-glycosylation sequon: N-{P}-[ST]-{P}
    sequence = "AANESTZZ"  # contains N-E-S-T at position 3
    matches = sequence_utils.motif_search(sequence, r"N[^P][ST][^P]")
    assert len(matches) == 1
    assert matches[0]["match"] == "NEST"


def test_is_uniprot_accession_valid_and_invalid():
    assert is_uniprot_accession("P04637")
    assert is_uniprot_accession("A0A023GPI8")
    assert not is_uniprot_accession("NOT_AN_ACCESSION")


def test_is_pdb_id_valid_and_invalid():
    assert is_pdb_id("1TUP")
    assert not is_pdb_id("ABCDE")


def test_parse_uniprot_entry_flattens_expected_fields():
    raw = {
        "primaryAccession": "P04637",
        "entryType": "UniProtKB reviewed (Swiss-Prot)",
        "proteinDescription": {"recommendedName": {"fullName": {"value": "Cellular tumor antigen p53"}}},
        "genes": [{"geneName": {"value": "TP53"}}],
        "organism": {"scientificName": "Homo sapiens"},
        "sequence": {"length": 393, "value": "MEEP..."},
        "comments": [{"commentType": "FUNCTION", "texts": [{"value": "Acts as a tumor suppressor."}]}],
    }
    parsed = parse_uniprot_entry(raw)
    assert parsed["accession"] == "P04637"
    assert parsed["protein_name"] == "Cellular tumor antigen p53"
    assert parsed["gene_names"] == ["TP53"]
    assert parsed["organism"] == "Homo sapiens"
    assert parsed["length"] == 393
    assert parsed["reviewed"] is True
    assert "tumor suppressor" in parsed["function"]


def test_parse_pubmed_esummary_extracts_articles():
    raw = {
        "result": {
            "uids": ["12345"],
            "12345": {
                "title": "A study of TP53",
                "authors": [{"name": "Doe J"}],
                "fulljournalname": "Journal of Examples",
                "pubdate": "2024",
                "articleids": [{"idtype": "doi", "value": "10.1000/example"}],
            },
        }
    }
    papers = parse_pubmed_esummary(raw)
    assert len(papers) == 1
    assert papers[0]["pmid"] == "12345"
    assert papers[0]["title"] == "A study of TP53"
    assert papers[0]["doi"] == "10.1000/example"
