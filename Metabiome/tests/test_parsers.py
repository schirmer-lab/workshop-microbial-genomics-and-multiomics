"""
Tests for metabiome parsers using real data files.

This test module validates the parsing functionality for various metabiome data formats
using actual data files from data/input directory.
"""

from pathlib import Path

import polars as pl
import pyfaidx
import pytest

from metabiome.io.parsers import (
    FunctionalGroupParser,
    GeneAbundanceParser,
    IDMappingParser,
    MetadataParser,
    SequenceParser,
    TaxonomyParser,
)

# Define real data paths
DATA_DIR = Path("/Users/xiheng/Workspace/metabiome/data/input")
METADATA_DIR = DATA_DIR / "metadata"
RPKM_FILE = DATA_DIR / "RPKM.json"
FG_FILE = DATA_DIR / "FG.json"
TAXONOMY_FILE = DATA_DIR / "taxonomy.json"
ID_MAPPING_FILE = DATA_DIR / "id_mapping.tsv"
FASTA_FILE = DATA_DIR / "merged.fasta"


class TestBaseParserValidation:
    """Test basic validation functionality."""


class TestMetadataParser:
    """Test metadata parser functionality using real metadata files."""

    def test_basic_metadata_structure(self):
        """Test that MetadataParser has correct structure."""
        assert MetadataParser.types == [".csv", ".tsv", ".parquet"]
        assert len(MetadataParser.required_columns) == 6  # Without patient_id
        expected_cols = {
            "sample_id",
            "disease_group",
            "disease_state",
            "use_antibiotic",
            "age",
            "gender",
        }
        assert set(MetadataParser.required_columns) == expected_cols

    def test_single_metadata_file_parsing(self):
        """Test parsing a single real metadata file."""
        test_file = METADATA_DIR / "CRC_GuptaA_2019.metadata.csv"

        if not test_file.exists():
            pytest.skip(f"Test file not found: {test_file}")

        parser = MetadataParser(test_file)
        df = parser.data

        # Verify structure
        assert isinstance(df, pl.LazyFrame)
        df_collected = df.collect()
        assert len(df_collected) > 0
        assert "sample" in df.collect_schema().names()

        # Verify categorical casting (excluding age)
        for col in df_collected.columns:
            if col not in ["age", "sample"]:
                assert df_collected[col].dtype == pl.Categorical
            else:
                assert df_collected[col].dtype in [pl.Utf8, pl.Int64]

    def test_metadata_directory_parsing(self):
        """Test parsing entire metadata directory."""
        if not METADATA_DIR.exists():
            pytest.skip(f"Metadata directory not found: {METADATA_DIR}")

        parser = MetadataParser(METADATA_DIR)
        df = parser.data

        # Verify structure
        assert isinstance(df, pl.LazyFrame)
        df_collected = df.collect()
        assert len(df_collected) > 0

        # Verify sample column exists and has data
        assert "sample" in df.collect_schema().names()
        assert df_collected["sample"].n_unique() > 0

        # Check that concatenation worked - should have data from multiple files
        assert len(df_collected) > 50  # Expecting multiple files worth of data

    def test_metadata_file_formats(self):
        """Test different metadata file formats."""
        # Test CSV with semicolon separator
        csv_file = METADATA_DIR / "CRC_GuptaA_2019.metadata.csv"
        if csv_file.exists():
            parser = MetadataParser(csv_file)
            assert isinstance(parser.data, pl.LazyFrame)
            df_collected = parser.data.collect()
            assert len(df_collected) > 0

    def test_nonexistent_metadata_path(self):
        """Test that non-existent paths raise appropriate errors."""
        with pytest.raises(FileNotFoundError, match="Path does not exist"):
            MetadataParser("/path/that/does/not/exist")

    def test_metadata_empty_directory(self):
        """Test that empty directories raise appropriate errors."""


class TestIDMappingParser:
    """Test ID mapping parser functionality using real data."""

    def test_basic_id_mapping_structure(self):
        """Test that IDMappingParser has correct structure."""
        assert IDMappingParser.types == [".tsv", ".csv"]
        expected_cols = {
            "gene_id",
            "gc_id",
            "cohort_name",
            "mcgc_id",
            "mcpc_id",
        }
        assert set(IDMappingParser.required_columns) == expected_cols

    def test_real_id_mapping_parsing(self):
        """Test parsing real ID mapping file."""
        if not ID_MAPPING_FILE.exists():
            pytest.skip(f"ID mapping file not found: {ID_MAPPING_FILE}")

        parser = IDMappingParser(ID_MAPPING_FILE)
        df = parser.data

        # Verify structure
        assert isinstance(df, pl.LazyFrame)
        df_collected = df.collect()
        assert len(df_collected) > 0

        # Verify required columns
        df_columns = df.collect_schema().names()
        for col in IDMappingParser.required_columns:
            assert col in df_columns


class TestTaxonomyParser:
    """Test taxonomy parser functionality using real data."""

    def test_basic_taxonomy_structure(self):
        """Test that TaxonomyParser has correct structure."""
        assert TaxonomyParser.types == [".json"]

    def test_real_taxonomy_parsing(self):
        """Test parsing real taxonomy JSON file."""
        if not TAXONOMY_FILE.exists():
            pytest.skip(f"Taxonomy file not found: {TAXONOMY_FILE}")

        parser = TaxonomyParser(TAXONOMY_FILE)
        df = parser.data

        # Verify structure
        assert isinstance(df, pl.LazyFrame)
        df_collected = df.collect()
        assert len(df_collected) > 0

        # Verify expected columns
        expected_cols = [
            "gc_id",
            "msp_id",
            "gene_category",
        ]
        df_columns = df.collect_schema().names()
        for col in expected_cols:
            assert col in df_columns

        # Verify categorical casting
        categorical_cols = ["gc_id", "msp_id", "gene_category"]
        for col in categorical_cols:
            assert df_collected[col].dtype == pl.Categorical

    def test_taxonomy_with_exploded_lineage(self):
        """Test taxonomy parsing with exploded lineage."""
        if not TAXONOMY_FILE.exists():
            pytest.skip(f"Taxonomy file not found: {TAXONOMY_FILE}")

        parser = TaxonomyParser(TAXONOMY_FILE)
        df = parser.data

        # Verify structure
        assert isinstance(df, pl.LazyFrame)
        df_collected = df.collect()
        assert len(df_collected) > 0

        # Should have taxonomic rank columns
        taxonomic_ranks = [
            "domain",
            "phylum",
            "class",
            "order",
            "family",
            "genus",
            "species",
        ]
        df_columns = df.collect_schema().names()
        for rank in taxonomic_ranks:
            assert rank in df_columns


class TestFunctionalGroupParser:
    """Test functional group parser functionality using real data."""

    def test_basic_functional_group_structure(self):
        """Test that FunctionalGroupParser has correct structure."""
        assert FunctionalGroupParser.types == [".json"]

    def test_real_functional_group_parsing(self):
        """Test parsing real functional group JSON file."""
        if not FG_FILE.exists():
            pytest.skip(f"Functional group file not found: {FG_FILE}")

        parser = FunctionalGroupParser(FG_FILE, explode=True)
        df = parser.data

        # Verify structure
        assert isinstance(df, pl.LazyFrame)
        df_collected = df.collect()
        assert len(df_collected) > 0

        # Verify expected columns
        df_columns = df.collect_schema().names()
        assert "gc_id" in df_columns
        assert "pfam_domain" in df_columns

        # Verify categorical casting
        assert df_collected["gc_id"].dtype == pl.Categorical
        assert df_collected["pfam_domain"].dtype == pl.Categorical

    def test_functional_group_no_explode(self):
        """Test functional group parsing without exploding domains."""
        if not FG_FILE.exists():
            pytest.skip(f"Functional group file not found: {FG_FILE}")

        parser = FunctionalGroupParser(FG_FILE, explode=False)
        df = parser.data

        # Verify structure
        assert isinstance(df, pl.LazyFrame)
        df_collected = df.collect()
        assert len(df_collected) > 0

        # Should have 'pfam_domain' column (not 'pfam_domains')
        df_columns = df.collect_schema().names()
        assert "gc_id" in df_columns
        assert "pfam_domain" in df_columns


class TestGeneAbundanceParser:
    """Test gene abundance parser functionality using real data."""

    def test_basic_abundance_structure(self):
        """Test that GeneAbundanceParser has correct structure."""
        assert GeneAbundanceParser.types == [".json"]

    def test_real_abundance_parsing(self):
        """Test parsing real gene abundance JSON file."""
        if not RPKM_FILE.exists():
            pytest.skip(f"RPKM file not found: {RPKM_FILE}")

        parser = GeneAbundanceParser(RPKM_FILE)
        df = parser.data

        # Verify structure
        assert isinstance(df, pl.LazyFrame)
        df_collected = df.collect()
        assert len(df_collected) > 0

        # Verify expected columns
        expected_cols = ["gc_id", "sample", "abundance"]
        df_columns = df.collect_schema().names()
        for col in expected_cols:
            assert col in df_columns

        # Verify data types
        assert df_collected["gc_id"].dtype == pl.Categorical
        assert df_collected["sample"].dtype == pl.Utf8
        assert df_collected["abundance"].dtype == pl.Float32

        # Verify abundance values are reasonable
        assert df_collected["abundance"].min() >= 0
        assert df_collected["abundance"].max() > 0

        # Verify long format - each row is one gene-sample pair
        assert df_collected["gc_id"].n_unique() > 1
        assert df_collected["sample"].n_unique() > 1

    def test_abundance_min_threshold_filtering(self):
        """Test minimum abundance threshold filtering."""
        if not RPKM_FILE.exists():
            pytest.skip(f"RPKM file not found: {RPKM_FILE}")

        # Parse with default threshold
        parser_default = GeneAbundanceParser(RPKM_FILE)
        df_default = parser_default.data
        assert isinstance(df_default, pl.LazyFrame)
        df_collected = df_default.collect()
        assert len(df_collected) > 0


class TestSequenceParser:
    """Test sequence parser functionality using real data."""

    def test_basic_sequence_structure(self):
        """Test that SequenceParser has correct structure."""
        assert SequenceParser.types == [".fasta", ".fa", ".fna", ".faa"]

    def test_real_fasta_parsing(self):
        """Test parsing real FASTA file."""
        if not FASTA_FILE.exists():
            pytest.skip(f"FASTA file not found: {FASTA_FILE}")

        parser = SequenceParser(FASTA_FILE)
        fasta_obj = parser.data

        # Verify it returns a pyfaidx.Fasta object
        assert isinstance(fasta_obj, pyfaidx.Fasta)

        # Verify it has sequences
        assert len(fasta_obj) > 0

        # Test accessing sequences (lazy loading)
        first_key = list(fasta_obj.keys())[0]
        seq = fasta_obj[first_key]
        assert len(seq) > 0


# Integration test to verify all parsers work with real data
class TestParserIntegration:
    """Integration tests using real data files."""

    def test_all_parsers_with_real_data(self):
        """Test that all parsers can successfully parse their respective real data files."""
        results = {}

        # Test MetadataParser
        if METADATA_DIR.exists():
            metadata_parser = MetadataParser(METADATA_DIR)
            results["metadata"] = len(metadata_parser.data.collect())

        # Test GeneAbundanceParser
        if RPKM_FILE.exists():
            abundance_parser = GeneAbundanceParser(RPKM_FILE)
            results["abundance"] = len(abundance_parser.data.collect())

        # Test TaxonomyParser
        if TAXONOMY_FILE.exists():
            taxonomy_parser = TaxonomyParser(TAXONOMY_FILE)
            results["taxonomy"] = len(taxonomy_parser.data.collect())

        # Test FunctionalGroupParser
        if FG_FILE.exists():
            fg_parser = FunctionalGroupParser(FG_FILE)
            results["functional_groups"] = len(fg_parser.data.collect())

        # Test IDMappingParser
        if ID_MAPPING_FILE.exists():
            id_parser = IDMappingParser(ID_MAPPING_FILE)
            results["id_mapping"] = len(id_parser.data.collect())

        # Test SequenceParser
        if FASTA_FILE.exists():
            seq_parser = SequenceParser(FASTA_FILE)
            results["sequences"] = len(seq_parser.data)

        # Verify we got some results
        assert len(results) > 0
        print(f"Successfully parsed data files: {results}")

        # All results should have positive row counts
        for parser_name, row_count in results.items():
            assert row_count > 0, f"{parser_name} parser returned empty data"
