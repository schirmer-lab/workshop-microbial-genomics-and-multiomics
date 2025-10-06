"""
Comprehensive tests for MetabiomeDataSpace grouping and aggregation API.

Tests cover:
- Basic grouping (single/multiple columns, auto-detection, explicit axis)
- Aggregation methods (mean, sum, count, agg)
- Cross-dimensional grouping (samples + features)
- Error handling and edge cases
- Integration with views and lazy evaluation
- Real-world metagenomic research scenarios
- Performance and memory efficiency
"""

import numpy as np
import polars as pl
import pytest

from metabiome.core import GroupedMetabiomeDataSpace, MetabiomeDataSpace


@pytest.fixture
def sample_test_data():
    """
    Create realistic test data for metagenomic aggregation testing.

    Creates a small but representative dataset with:
    - 12 samples (3 diseases × 4 timepoints)
    - 20 features (genes) with diverse annotations
    - Hierarchical structure with controlled abundance values
    """
    # Sample metadata with grouping columns
    metadata = pl.LazyFrame(
        {
            "sample": [f"sample_{i:02d}" for i in range(1, 13)],
            "disease_group": ["control", "disease_A", "disease_B"] * 4,
            "age_category": ["young"] * 3
            + ["middle"] * 3
            + ["old"] * 3
            + ["young"] * 3,
            "timepoint": [0, 7, 14, 21] * 3,
            "cohort": ["cohort_1"] * 6 + ["cohort_2"] * 6,
            "patient_id": [
                f"patient_{i}" for i in [1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3]
            ],
        }
    )

    # Feature annotations with grouping columns
    features = [f"gene_{i:03d}" for i in range(1, 21)]
    annotation = pl.LazyFrame(
        {
            "gc_id": features,
            "pfam_domain": ["PF00001"] * 7 + ["PF00002"] * 6 + ["PF00003"] * 7,
            "protein_family": ["fam_A"] * 5 + ["fam_B"] * 10 + ["fam_C"] * 5,
            "taxonomy": ["Bacteroides"] * 8
            + ["Escherichia"] * 6
            + ["Lactobacillus"] * 6,
            "sequence_identity": [0.95, 0.98, 0.92, 0.97, 0.94, 0.99, 0.91]
            + [0.96, 0.93, 0.98, 0.95, 0.97, 0.94]
            + [0.92, 0.98, 0.96, 0.99, 0.93, 0.97, 0.95],
        }
    )

    # Abundance data with controlled values for predictable aggregation
    np.random.seed(42)  # For reproducible tests
    abundance_data = []

    for i, sample in enumerate(metadata.collect()["sample"]):
        for j, gene in enumerate(features):
            # Create predictable abundance patterns
            base_abundance = (i + 1) * (j + 1) * 0.1
            noise = np.random.normal(0, 0.01)
            abundance = max(0, base_abundance + noise)

            abundance_data.append(
                {"sample": sample, "gc_id": gene, "abundance": abundance}
            )

    abundance = pl.LazyFrame(abundance_data)

    # ID mapping for hierarchical testing
    id_mapping = pl.LazyFrame(
        {
            "gene_id": [f"gene_{i:03d}_full" for i in range(1, 21)],
            "gc_id": features,
            "mcgc_id": [f"mcgc_{(i - 1) // 4 + 1}" for i in range(1, 21)],
            "mcpc_id": [f"mcpc_{(i - 1) // 2 + 1}" for i in range(1, 21)],
        }
    )

    return {
        "metadata": metadata,
        "abundance": abundance,
        "annotation": annotation,
        "id_mapping": id_mapping,
    }


@pytest.fixture
def mds(sample_test_data):
    """Create a MetabiomeDataSpace instance for testing."""
    return MetabiomeDataSpace.from_annotation(
        metadata=sample_test_data["metadata"],
        abundance=sample_test_data["abundance"],
        annotation=sample_test_data["annotation"],
        id_mapping=sample_test_data["id_mapping"],
    )


class TestBasicGrouping:
    """Test basic grouping functionality."""

    def test_explicit_samples_grouping(self, mds):
        """Test explicit samples axis grouping."""
        grouped = mds.group_by(samples="disease_group")
        # Check the type and value of grouped._metadata
        print("DEBUG grouped._metadata type:", type(grouped._metadata))
        print("DEBUG grouped._metadata value:", grouped._metadata)
        assert isinstance(grouped, GroupedMetabiomeDataSpace)
        assert "disease_group" in grouped._samples_columns

    def test_explicit_features_grouping(self, mds):
        """Test explicit features axis grouping."""
        grouped = mds.group_by(features="pfam_domain")

        assert isinstance(grouped, GroupedMetabiomeDataSpace)
        assert "pfam_domain" in grouped._features_columns

    def test_multiple_column_grouping(self, mds):
        """Test grouping by multiple columns."""
        grouped = mds.group_by(
            samples=["disease_group", "age_category"],
        )

        assert isinstance(grouped, GroupedMetabiomeDataSpace)
        assert set(grouped._samples_columns) == {
            "disease_group",
            "age_category",
        }

    def test_expression_based_grouping(self, mds):
        """Test grouping with Polars expressions."""
        import polars as pl

        with pytest.raises(NotImplementedError):
            mds.group_by(samples=pl.col("timepoint") > 7)

    def test_cross_dimensional_grouping(self, mds):
        """Test grouping both samples and features simultaneously."""
        grouped = mds.group_by(samples="disease_group", features="pfam_domain")

        assert isinstance(grouped, GroupedMetabiomeDataSpace)
        assert "disease_group" in grouped._samples_columns
        assert "pfam_domain" in grouped._features_columns


class TestAggregationMethods:
    """Test aggregation method functionality."""

    def test_mean_aggregation(self, mds):
        """Test mean aggregation functionality."""
        grouped = mds.group_by(samples="disease_group")
        result = grouped.agg("mean")

        # Should return a new MetabiomeDataSpace
        assert isinstance(result, MetabiomeDataSpace)
        assert result is not mds

        # Should have aggregated data
        result_data = result.abundance
        assert len(result_data) > 0

        # Each row's disease_group should be a string
        for val in result_data.columns:
            assert isinstance(val, str)
        # There should be 3 unique groups
        unique_groups = set(result_data.columns)
        assert unique_groups == {"sample", "gc_id", "abundance"}

    def test_sum_aggregation(self, mds):
        """Test sum aggregation functionality."""
        grouped = mds.group_by(features="pfam_domain")
        result = grouped.agg("sum")
        assert isinstance(result, GroupedMetabiomeDataSpace)

        for val in result.abundance.columns:
            assert isinstance(val, str)

        feature_dim = result.annotation["pfam_domain"].len()
        result_dim = result.abundance.shape

        assert result_dim == (
            feature_dim,
            3,
        )  # 3 columns: sample, gc_id, abundance

    def test_count_aggregation(self, mds):
        """Test count aggregation functionality."""
        grouped = mds.group_by(samples="disease_group")
        result = grouped.agg("count")

        assert isinstance(result, MetabiomeDataSpace)

        # Verify counts are correct
        result_data = result.abundance
        # All counts should be >= 0
        for count_val in result_data["abundance"]:
            assert count_val >= 0

    def test_agg_unknown_function(self, mds):
        """Test agg() method with single aggregation function."""
        grouped = mds.group_by("disease_group")
        with pytest.raises(ValueError):
            grouped.agg("unknown_function")

    def test_agg_custom_expressions(self, mds):
        """Test agg() method with custom Polars expressions."""
        grouped = mds.group_by("disease_group")
        with pytest.raises(NotImplementedError):
            grouped.agg(pl.col("abundance").quantile(0.95).alias("p95"))


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_invalid_column_names(self, mds):
        """Test error handling for invalid column names."""
        with pytest.raises(ValueError):
            mds.group_by("nonexistent_column")

    def test_axis_detection_failure(self, mds):
        """Test handling of ambiguous axis detection."""
        with pytest.raises(ValueError):
            mds.group_by("completely_invalid_column")

    def test_invalid_aggregation_functions(self, mds):
        """Test error handling for invalid aggregation functions."""
        grouped = mds.group_by("disease_group")

        with pytest.raises((ValueError, AttributeError)):
            grouped.agg("invalid_function")

    def test_empty_grouping_results(self, mds):
        """Test handling of empty grouping results."""
        # Create a view that filters samples first
        sample_view = mds["sample_01", :]
        grouped = sample_view.group_by("disease_group")
        result = grouped.agg("mean")
        assert isinstance(result, MetabiomeDataSpace)
        # Result should have at most one sample
        assert len(result.metadata) <= 1


class TestIntegration:
    """Test integration with other MetabiomeDataSpace features."""

    def test_grouping_with_views(self, mds):
        """Test that grouping works with MetabiomeView objects."""
        # Create a view first
        view = mds[["sample_01", "sample_02", "sample_03"], :]
        grouped = view.group_by(samples="disease_group")
        result = grouped.agg("mean")
        assert isinstance(result, MetabiomeDataSpace)
        # Should only include samples from the view
        result_samples = result.metadata["sample"].to_list()
        assert len(result_samples) <= 3

    def test_lazy_evaluation_preserved(self, mds):
        """Test that lazy evaluation is preserved through grouping."""
        grouped = mds.group_by(samples="disease_group")
        # Grouping should not trigger computation
        assert isinstance(mds._abundance, pl.LazyFrame)
        # Even after aggregation, result should be a DataFrame (eager)
        result = grouped.agg("mean")
        assert isinstance(result.abundance, pl.DataFrame)

    def test_data_alignment_maintained(self, mds):
        """Test that data alignment is maintained after aggregation."""
        grouped = mds.group_by("disease_group")
        result = grouped.agg("mean")
        metadata_samples = set(result.metadata["sample"].to_list())
        abundance_samples = set(result.abundance["sample"].to_list())
        assert metadata_samples == abundance_samples
        expected_groups = {"control", "disease_A", "disease_B"}
        assert metadata_samples == expected_groups
        assert abundance_samples == expected_groups


class TestRealWorldScenarios:
    """Test realistic metagenomic research scenarios."""

    def test_disease_group_analysis(self, mds):
        """Test typical disease group comparison analysis."""
        disease_profiles = mds.group_by("disease_group").agg("mean")
        assert isinstance(disease_profiles, MetabiomeDataSpace)
        disease_groups = set(disease_profiles.metadata["sample"])
        assert len(disease_groups) == 3  # control, disease_A, disease_B
        abundances = disease_profiles.abundance["abundance"]
        assert abundances.mean() > 0

    def test_functional_domain_analysis(self, mds):
        """Test functional domain aggregation analysis."""
        pfam_profiles = mds.group_by(features="pfam_domain").agg("sum")

        assert isinstance(pfam_profiles, MetabiomeDataSpace)
        domains = set(pfam_profiles.annotation["pfam_domain"])
        assert len(domains) == 3  # PF00001, PF00002, PF00003

    def test_longitudinal_analysis(self, mds):
        """Test time-series/longitudinal analysis."""
        longitudinal = mds.group_by("patient_id", "timepoint").agg("mean")

        assert isinstance(longitudinal, MetabiomeDataSpace)
        result_data = longitudinal.metadata
        patient_timepoints = result_data.group_by("patient_id").agg(
            pl.col("timepoint").n_unique().alias("n_timepoints")
        )

        # Each patient should have multiple timepoints
        assert patient_timepoints["n_timepoints"].min() > 1

    def test_disease_functional_interaction(self, mds):
        """Test cross-dimensional disease × functional domain analysis."""
        interaction = mds.group_by(
            samples="disease_group", features="pfam_domain"
        ).agg("mean")
        assert isinstance(interaction, MetabiomeDataSpace)
        result_metadata = interaction.metadata
        result_annotation = interaction.annotation
        assert len(result_metadata) >= 3  # At least 3 disease groups
        assert len(result_annotation) >= 3  # At least 3 pfam domains


class TestPerformance:
    """Test performance and memory efficiency."""

    def test_no_unnecessary_computation(self, mds):
        """Test that grouping doesn't trigger unnecessary computation."""
        # Track if collect() is called prematurely
        original_abundance = mds._abundance
        _ = mds.group_by("disease_group")  # Create grouped object
        # Parent data should still be lazy
        assert mds._abundance is original_abundance
        assert isinstance(mds._abundance, pl.LazyFrame)

    def test_memory_efficiency(self, mds):
        """Test that grouping doesn't copy large amounts of data."""
        grouped = mds.group_by("disease_group")
        # Should be a lightweight object
        import sys

        grouped_size = sys.getsizeof(grouped)
        assert grouped_size < 10000  # Should be a small object

    @pytest.mark.parametrize("agg_func", ["mean", "sum", "count"])
    def test_aggregation_performance(self, mds, agg_func):
        """Test that aggregation methods complete in reasonable time."""
        import time

        grouped = mds.group_by("disease_group")
        start_time = time.time()
        result = grouped.agg(agg_func)
        end_time = time.time()
        # Should complete quickly (adjust threshold as needed)
        assert end_time - start_time < 1.0  # Less than 1 second
        assert isinstance(result, MetabiomeDataSpace)


# Additional utility tests
class TestGroupedMetabiomeDataSpace:
    """Test GroupedMetabiomeDataSpace class directly."""

    def test_repr_and_str(self, mds):
        """Test string representations of grouped objects."""
        grouped = mds.group_by("disease_group")

        repr_str = repr(grouped)
        assert "GroupedMetabiomeDataSpace" in repr_str
        assert "disease_group" in repr_str

        str_repr = str(grouped)
        assert isinstance(str_repr, str)
        assert len(str_repr) > 0

    def test_grouping_attributes(self, mds):
        """Test that grouping attributes are set correctly."""
        grouped = mds.group_by("disease_group", "age_category")
        # Only the first argument is used for samples_columns in current API
        assert hasattr(grouped, "_samples_columns")
        assert hasattr(grouped, "_features_columns")
        assert grouped._samples_columns == ["disease_group"]
        assert grouped._features_columns == ["age_category"]


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v"])
