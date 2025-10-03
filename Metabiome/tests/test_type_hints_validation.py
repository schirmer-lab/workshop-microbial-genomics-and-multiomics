#!/usr/bin/env python3
"""
Test suite for the centralized validate_index function.

This module tests the shared indexing validation logic used across
MetabiomeDataSpace and MetabiomeView to ensure consistency and robustness.
"""

import numpy as np
import polars as pl
import pytest

from metabiome.core.indexing import validate_index


class TestValidateIndex:
    """Test cases for the centralized validate_index function."""

    def test_string_index_valid(self):
        """Test validation of single string (biological ID)."""
        result = validate_index("sample_01", "samples")
        assert result == "sample_01"
        assert isinstance(result, str)

    def test_string_list_valid(self):
        """Test validation of list of strings (biological IDs)."""
        sample_ids = ["sample_01", "sample_02", "sample_03"]
        result = validate_index(sample_ids, "samples")
        assert result == sample_ids
        assert isinstance(result, list)
        assert all(isinstance(x, str) for x in result)

    def test_string_tuple_valid(self):
        """Test validation of tuple of strings (biological IDs)."""
        sample_ids = ("sample_01", "sample_02", "sample_03")
        result = validate_index(sample_ids, "samples")
        assert result == list(sample_ids)  # Convert to list
        assert isinstance(result, list)
        assert all(isinstance(x, str) for x in result)

    def test_numpy_array_strings_valid(self):
        """Test validation of numpy array containing strings."""
        sample_ids = np.array(["sample_01", "sample_02", "sample_03"])
        result = validate_index(sample_ids, "samples")
        expected = ["sample_01", "sample_02", "sample_03"]
        assert result == expected
        assert isinstance(result, list)
        assert all(isinstance(x, str) for x in result)

    def test_generator_strings_valid(self):
        """Test validation of generator yielding strings."""

        def string_generator():
            yield "sample_01"
            yield "sample_02"
            yield "sample_03"

        result = validate_index(string_generator(), "samples")
        expected = ["sample_01", "sample_02", "sample_03"]
        assert result == expected
        assert isinstance(result, list)

    def test_set_strings_valid(self):
        """Test validation of set containing strings."""
        sample_set = {"sample_01", "sample_02", "sample_03"}
        result = validate_index(sample_set, "samples")
        expected = ["sample_01", "sample_02", "sample_03"]
        assert sorted(result) == sorted(expected)  # Set order may vary
        assert isinstance(result, list)

    def test_empty_list_valid(self):
        """Test validation of empty list."""
        result = validate_index([], "samples")
        assert result == []
        assert isinstance(result, list)

    def test_empty_tuple_valid(self):
        """Test validation of empty tuple."""
        result = validate_index((), "samples")
        assert result == []
        assert isinstance(result, list)

    def test_none_valid(self):
        """Test validation of None (select all)."""
        result = validate_index(None, "samples")
        assert result is None

    def test_slice_none_valid(self):
        """Test validation of slice(None) (select all)."""
        result = validate_index(slice(None), "samples")
        assert result == slice(None)
        assert isinstance(result, slice)

    def test_polars_expression_valid(self):
        """Test validation of Polars expression."""
        expr = pl.col("timepoint") > 5
        result = validate_index(expr, "samples")
        assert result is expr
        assert isinstance(result, pl.Expr)

    def test_single_integer_invalid(self):
        """Test that single integer raises ValueError."""
        with pytest.raises(
            ValueError, match="Positional indexing with int is not supported"
        ):
            validate_index(5, "samples")

    def test_integer_list_invalid(self):
        """Test that list of integers raises ValueError."""
        with pytest.raises(
            ValueError,
            match="Positional indexing with integer lists is not supported",
        ):
            validate_index([1, 2, 3], "samples")

    def test_numpy_array_integers_invalid(self):
        """Test that numpy array of integers raises ValueError."""
        int_array = np.array([1, 2, 3])
        with pytest.raises(
            ValueError,
            match="mixed or invalid element types",
        ):
            validate_index(int_array, "samples")

    def test_slice_invalid(self):
        """Test that slice (other than slice(None)) raises ValueError."""
        with pytest.raises(
            ValueError, match="Positional indexing with slice is not supported"
        ):
            validate_index(slice(1, 5), "samples")

        with pytest.raises(
            ValueError, match="Positional indexing with slice is not supported"
        ):
            validate_index(slice(1, None), "samples")

    def test_mixed_types_invalid(self):
        """Test that mixed type list raises ValueError."""
        with pytest.raises(ValueError, match="mixed or invalid element types"):
            validate_index(["sample_01", 2, "sample_03"], "samples")

    def test_unsupported_type_invalid(self):
        """Test that unsupported types raise ValueError."""
        # Dict should be rejected as unsupported type (not iterable over IDs)
        with pytest.raises(ValueError, match="Unsupported samples type"):
            validate_index({"key": "value"}, "samples")

        with pytest.raises(ValueError, match="Unsupported samples type"):
            validate_index(42.5, "samples")

    def test_custom_index_name_in_error(self):
        """Test that custom index name appears in error messages."""
        with pytest.raises(ValueError, match="features"):
            validate_index(5, "features")

        with pytest.raises(ValueError, match="gene_catalog"):
            validate_index([1, 2, 3], "gene_catalog")

    def test_bytes_invalid(self):
        """Test that bytes objects are rejected."""
        with pytest.raises(ValueError, match="Unsupported samples type"):
            validate_index(b"sample_01", "samples")

    def test_edge_case_empty_generator(self):
        """Test empty generator."""

        def empty_generator():
            return
            yield  # This will never execute

        result = validate_index(empty_generator(), "samples")
        assert result == []
        assert isinstance(result, list)

    def test_edge_case_single_element_iterables(self):
        """Test single-element iterables."""
        # Single string in list
        result = validate_index(["sample_01"], "samples")
        assert result == ["sample_01"]

        # Single integer in list (should still fail)
        with pytest.raises(
            ValueError, match="Positional indexing with integer lists"
        ):
            validate_index([5], "samples")

    def test_numpy_array_mixed_types_invalid(self):
        """Test numpy array with mixed types."""
        # NumPy will convert to strings, but let's test the edge case
        mixed_array = np.array(
            ["sample_01", "sample_02"]
        )  # All strings, should work
        result = validate_index(mixed_array, "samples")
        assert result == ["sample_01", "sample_02"]

        # Test what happens with object array
        obj_array = np.array(["sample_01", 2], dtype=object)
        with pytest.raises(ValueError, match="mixed or invalid element types"):
            validate_index(obj_array, "samples")


class TestValidateIndexIntegration:
    """Integration tests to ensure validate_index works with actual data structures."""

    def test_polars_expressions_realistic(self):
        """Test realistic Polars expressions."""

        # Test various expression types
        expr1 = pl.col("timepoint") > 5
        result1 = validate_index(expr1, "samples")
        assert isinstance(result1, pl.Expr)

        expr2 = pl.col("group") == "A"
        result2 = validate_index(expr2, "samples")
        assert isinstance(result2, pl.Expr)

        expr3 = pl.col("sample").str.contains("sample_0[12]")
        result3 = validate_index(expr3, "samples")
        assert isinstance(result3, pl.Expr)

    def test_real_world_id_patterns(self):
        """Test real-world biological ID patterns."""
        # Gene catalog IDs
        gc_ids = ["GC_001", "GC_002", "GC_003"]
        result = validate_index(gc_ids, "features")
        assert result == gc_ids

        # Sample IDs with complex patterns
        sample_ids = [
            "SRR12345678",
            "ERR987654321",
            "DRR456789012",
            "patient_01_timepoint_0",
            "ctrl_group_A_rep_1",
        ]
        result = validate_index(sample_ids, "samples")
        assert result == sample_ids

        # MCGC/MCPC IDs
        cluster_ids = ["MCGC_00001", "MCGC_00002", "MCPC_00001"]
        result = validate_index(cluster_ids, "clusters")
        assert result == cluster_ids

    def test_backwards_compatibility(self):
        """Ensure validate_index maintains backwards compatibility."""
        # Test that old calling patterns still work

        # Single ID
        assert validate_index("sample_01") == "sample_01"

        # List of IDs
        ids = ["sample_01", "sample_02"]
        assert validate_index(ids) == ids

        # Polars expression
        expr = pl.col("timepoint") > 0
        assert validate_index(expr) is expr

        # None/slice(None)
        assert validate_index(None) is None
        assert validate_index(slice(None)) == slice(None)
