#!/usr/bin/env python3
"""
Test suite for MetabiomeView indexing functionality.

Tests include:
1. ID-based indexing with synthetic data
2. Expression-based indexing patterns
3. Positional indexing validation (should raise errors)
4. Integration testing with file-based data
"""

from pathlib import Path

import polars as pl
import pytest

import metabiome.io as mio
from metabiome.core.space import MetabiomeDataSpace


class TestIDBasedIndexing:
    """Test ID-based indexing functionality with synthetic data."""

    @pytest.fixture
    def synthetic_data(self):
        """Create synthetic test data for controlled testing."""
        metadata = pl.LazyFrame(
            {
                "sample": [f"sample_{i:02d}" for i in range(10)],
                "group": ["A"] * 5 + ["B"] * 5,
                "timepoint": list(range(10)),
            }
        )

        abundance = pl.LazyFrame(
            {
                "sample": [f"sample_{i:02d}" for i in range(10)]
                * 6,  # 10 samples x 6 features = 60 rows
                "gc_id": [f"gene_{j:02d}" for j in range(6)] * 10,
                "abundance": [
                    i * j + 1 for i in range(10) for j in range(6)
                ],  # Add 1 to avoid zeros
            }
        )

        annotation = pl.LazyFrame(
            {
                "gc_id": [f"gene_{i:02d}" for i in range(6)],
                "taxonomy": [f"species_{i}" for i in range(6)],
            }
        )

        return MetabiomeDataSpace.from_filtered_data(
            metadata=metadata, abundance=abundance, annotation=annotation
        )

    def test_basic_view_creation(self, synthetic_data):
        """Test basic view creation without indexing."""
        view = synthetic_data[:]  # Create a view using slice notation
        assert view is not None
        assert hasattr(view, "metadata")
        assert hasattr(view, "abundance")
        assert hasattr(view, "annotation")

    def test_sample_id_indexing(self, synthetic_data):
        """Test indexing with specific sample IDs."""
        sample_ids = ["sample_00", "sample_01", "sample_02"]
        view = synthetic_data[sample_ids]

        assert view is not None
        if view.abundance is not None:
            samples = view.abundance["sample"].unique().to_list()
            assert len(samples) == 3
            for sample_id in sample_ids:
                assert sample_id in samples

    def test_feature_id_indexing(self, synthetic_data):
        """Test indexing with specific feature IDs."""
        feature_ids = ["gene_00", "gene_01", "gene_02"]
        view = synthetic_data[:, feature_ids]

        assert view is not None
        if view.abundance is not None:
            features = view.abundance["gc_id"].unique().to_list()
            assert len(features) == 3
            for feature_id in feature_ids:
                assert feature_id in features

    def test_combined_id_indexing(self, synthetic_data):
        """Test combined sample and feature ID indexing."""
        sample_ids = ["sample_00", "sample_01"]
        feature_ids = ["gene_00", "gene_01", "gene_02"]
        view = synthetic_data[sample_ids, feature_ids]

        assert view is not None
        if view.abundance is not None:
            samples = view.abundance["sample"].unique().to_list()
            features = view.abundance["gc_id"].unique().to_list()

            assert len(samples) == 2
            assert len(features) == 3

            for sample_id in sample_ids:
                assert sample_id in samples
            for feature_id in feature_ids:
                assert feature_id in features

    def test_colon_notation_all_samples_specific_features(self, synthetic_data):
        """Test mds[:, features] - all samples, specific features."""
        feature_ids = ["gene_00", "gene_01", "gene_02"]
        view = synthetic_data[:, feature_ids]

        assert view is not None
        if view.abundance is not None:
            # Should have all 10 samples
            sample_count = view.abundance["sample"].n_unique()
            assert sample_count == 10

            # Should have exactly 3 features
            feature_count = view.abundance["gc_id"].n_unique()
            assert feature_count == 3

    def test_colon_notation_specific_samples_all_features(self, synthetic_data):
        """Test mds[samples, :] - specific samples, all features."""
        sample_ids = ["sample_00", "sample_01", "sample_02"]
        view = synthetic_data[sample_ids, :]

        assert view is not None
        if view.abundance is not None:
            # Should have exactly 3 samples
            sample_count = view.abundance["sample"].n_unique()
            assert sample_count == 3

            # Should have all 6 features
            feature_count = view.abundance["gc_id"].n_unique()
            assert feature_count == 6

    def test_colon_notation_all_data(self, synthetic_data):
        """Test mds[:] - all data (no filtering)."""
        view = synthetic_data[:]

        assert view is not None
        if view.abundance is not None:
            # Should have all samples and features
            sample_count = view.abundance["sample"].n_unique()
            feature_count = view.abundance["gc_id"].n_unique()

            assert sample_count == 10
            assert feature_count == 6

    def test_chained_id_indexing(self, synthetic_data):
        """Test chained ID-based indexing operations."""
        # Start with sample filter, then add feature filter
        view1 = synthetic_data[["sample_00", "sample_01", "sample_02"]]
        view2 = view1[:, ["gene_00", "gene_01"]]

        assert view2 is not None
        if view2.abundance is not None:
            sample_count = view2.abundance["sample"].n_unique()
            feature_count = view2.abundance["gc_id"].n_unique()

            assert sample_count == 3
            assert feature_count == 2


class TestExpressionBasedIndexing:
    """Test expression-based indexing patterns."""

    @pytest.fixture
    def synthetic_data(self):
        """Create synthetic test data for controlled testing."""
        metadata = pl.LazyFrame(
            {
                "sample": [f"sample_{i:02d}" for i in range(10)],
                "group": ["A"] * 5 + ["B"] * 5,
                "timepoint": list(range(10)),
            }
        )

        abundance = pl.LazyFrame(
            {
                "sample": [f"sample_{i:02d}" for i in range(10)] * 6,
                "gc_id": [f"gene_{j:02d}" for j in range(6)] * 10,
                "abundance": [i * j + 1 for i in range(10) for j in range(6)],
            }
        )

        annotation = pl.LazyFrame(
            {
                "gc_id": [f"gene_{i:02d}" for i in range(6)],
                "taxonomy": [f"species_{i}" for i in range(6)],
            }
        )

        return MetabiomeDataSpace.from_filtered_data(
            metadata=metadata, abundance=abundance, annotation=annotation
        )

    def test_expression_based_sample_filtering(self, synthetic_data):
        """Test expression-based filtering on metadata."""
        view = synthetic_data[pl.col("group") == "A"]

        assert view is not None
        if view.metadata is not None:
            groups = view.metadata["group"].unique().to_list()
            assert groups == ["A"]

    def test_expression_based_timepoint_filtering(self, synthetic_data):
        """Test expression-based filtering on timepoint."""
        view = synthetic_data[pl.col("timepoint") > 5]

        assert view is not None
        if view.metadata is not None:
            timepoints = view.metadata["timepoint"].to_list()
            assert all(t > 5 for t in timepoints)


class TestPositionalIndexingValidation:
    """Test that positional indexing raises appropriate errors."""

    @pytest.fixture
    def synthetic_data(self):
        """Create minimal test data."""
        metadata = pl.DataFrame({"sample": ["s1", "s2", "s3"]})
        abundance = pl.DataFrame(
            {
                "sample": ["s1", "s2", "s3"],
                "gc_id": ["g1", "g2", "g3"],
                "abundance": [1, 2, 3],
            }
        )
        annotation = pl.DataFrame({"gc_id": ["g1", "g2", "g3"]})

        return MetabiomeDataSpace.from_filtered_data(
            metadata=metadata, abundance=abundance, annotation=annotation
        )

    def test_integer_indexing_raises_error(self, synthetic_data):
        """Test that integer indexing raises ValueError."""
        with pytest.raises(
            ValueError, match="Positional indexing.*int.*not supported"
        ):
            synthetic_data[0]

    def test_slice_indexing_raises_error(self, synthetic_data):
        """Test that slice indexing raises ValueError."""
        with pytest.raises(
            ValueError, match="Positional indexing.*slice.*not supported"
        ):
            synthetic_data[1:3]

    def test_integer_list_indexing_raises_error(self, synthetic_data):
        """Test that integer list indexing raises ValueError."""
        with pytest.raises(
            ValueError,
            match="Positional indexing.*integer lists.*not supported",
        ):
            synthetic_data[[0, 1, 2]]

    def test_2d_integer_indexing_raises_error(self, synthetic_data):
        """Test that 2D integer indexing raises ValueError."""
        with pytest.raises(
            ValueError, match="Positional indexing.*int.*not supported"
        ):
            synthetic_data[0, 1]

    def test_2d_slice_indexing_raises_error(self, synthetic_data):
        """Test that 2D slice indexing raises ValueError."""
        with pytest.raises(
            ValueError, match="Positional indexing.*slice.*not supported"
        ):
            synthetic_data[1:3, 0:2]

    def test_view_integer_indexing_raises_error(self, synthetic_data):
        """Test that view integer indexing raises ValueError."""
        view = synthetic_data[:]
        with pytest.raises(
            ValueError, match="Positional indexing.*int.*not supported"
        ):
            view[0]

    def test_view_slice_indexing_raises_error(self, synthetic_data):
        """Test that view slice indexing raises ValueError."""
        view = synthetic_data[:]
        with pytest.raises(
            ValueError, match="Positional indexing.*slice.*not supported"
        ):
            view[1:3]


class TestRealDataIndexing:
    """Test indexing with real data if available."""

    @pytest.fixture
    def real_data(self):
        """Load real test data if available, otherwise skip tests."""
        data_dir = Path("data/input")
        if not data_dir.exists():
            pytest.skip("Test data directory not found")

        try:
            return mio.from_files(
                metadata_path=data_dir / "metadata",
                abundance_path=data_dir / "RPKM.json",
                taxonomy_path=data_dir / "taxonomy.json",
                functional_path=data_dir / "FG.json",
                sequences_path=data_dir / "merged.fasta",
                id_mapping_path=data_dir / "id_mapping.tsv",
            )
        except Exception as e:
            pytest.skip(f"Could not load test data: {e}")

    def test_single_sample_indexing(self, real_data):
        """Test indexing with a single sample."""
        if real_data.metadata is None:
            pytest.skip("No metadata available")

        samples = (
            real_data.metadata.select("sample").unique()["sample"].to_list()
        )
        if len(samples) == 0:
            pytest.skip("No samples available")

        single_sample = samples[0]
        view = real_data[single_sample]

        assert view is not None
        assert view.abundance is not None

    def test_multiple_samples_indexing(self, real_data):
        """Test indexing with multiple samples."""
        if real_data.metadata is None:
            pytest.skip("No metadata available")

        samples = (
            real_data.metadata.select("sample").unique()["sample"].to_list()
        )
        if len(samples) < 3:
            pytest.skip("Not enough samples for test")

        sample_list = samples[:3]
        view = real_data[sample_list]

        assert view is not None
        assert view.abundance is not None

        # Verify the correct samples are included
        if view.abundance is not None:
            abundance_samples = (
                view.abundance.select("sample").unique()["sample"].to_list()
            )
            for sample in sample_list:
                assert sample in abundance_samples


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_data(self):
        """Test with empty data structures."""
        empty_metadata = pl.DataFrame({"sample": []})
        empty_abundance = pl.DataFrame(
            {"sample": [], "gc_id": [], "abundance": []}
        )
        empty_annotation = pl.DataFrame({"gc_id": []})

        mds = MetabiomeDataSpace.from_filtered_data(
            metadata=empty_metadata,
            abundance=empty_abundance,
            annotation=empty_annotation,
        )

        view = mds[:]  # Create a view using slice notation
        assert view is not None

    def test_nonexistent_sample_ids(self):
        """Test indexing with non-existent sample IDs."""
        metadata = pl.DataFrame({"sample": ["s1", "s2"]})
        abundance = pl.DataFrame(
            {"sample": ["s1", "s2"], "gc_id": ["g1", "g2"], "abundance": [1, 2]}
        )
        annotation = pl.DataFrame({"gc_id": ["g1", "g2"]})

        mds = MetabiomeDataSpace.from_filtered_data(
            metadata=metadata, abundance=abundance, annotation=annotation
        )

        # Should not raise error, but might return empty results
        view = mds[["nonexistent_sample"]]
        assert view is not None


if __name__ == "__main__":
    pytest.main(["-v", __file__], plugins=["pytester"])
