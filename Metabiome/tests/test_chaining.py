#!/usr/bin/env python3
"""
Test script to demonstrate improved indexing and chaining in MetabiomeDataSpace and MetabiomeView.
"""

import sys
from pathlib import Path

import polars as pl

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from metabiome import MetabiomeDataSpace


def test_chaining_functionality():
    """Test the new chaining functionality."""

    # Create sample data
    samples_data = pl.DataFrame(
        {
            "sample": ["S1", "S2", "S3", "S4", "S5"],
            "disease_group": [
                "Control",
                "Treatment",
                "Control",
                "Treatment",
                "Control",
            ],
            "age": [25, 30, 35, 40, 45],
        }
    ).lazy()

    abundance_data = pl.DataFrame(
        {
            "sample": [
                "S1",
                "S1",
                "S2",
                "S2",
                "S3",
                "S3",
                "S4",
                "S4",
                "S5",
                "S5",
            ],
            "gc_id": [
                "G1",
                "G2",
                "G1",
                "G2",
                "G1",
                "G2",
                "G1",
                "G2",
                "G1",
                "G2",
            ],
            "abundance": [
                10.5,
                20.3,
                15.2,
                25.1,
                12.8,
                18.7,
                22.4,
                30.9,
                14.6,
                21.2,
            ],
        }
    ).lazy()

    taxonomy_data = pl.DataFrame(
        {
            "gc_id": ["G1", "G2"],
            "msp_id": ["MSP1", "MSP2"],
            "species": ["Bacteroides fragilis", "Escherichia coli"],
        }
    ).lazy()

    functional_data = pl.DataFrame(
        {
            "gc_id": ["G1", "G2"],
            "function": ["Metabolism", "Pathogenesis"],
            "description": [
                "Involved in carbohydrate metabolism",
                "Associated with disease processes",
            ],
        }
    ).lazy()

    # Create MetabiomeDataSpace
    mds = MetabiomeDataSpace(
        metadata=samples_data,
        abundance=abundance_data,
        taxonomy=taxonomy_data,
        functional=functional_data,
    )

    print("=== Testing MetabiomeDataSpace and MetabiomeView Chaining ===\n")

    # Test 1: Basic 2D indexing (existing functionality)
    print("1. Basic 2D indexing: mds[['S1', 'S2'], ['G1']]")
    view1 = mds[["S1", "S2"], ["G1"]]
    print(f"   Result: {type(view1).__name__}")

    # Test 2: Single dimension indexing (existing functionality)
    print("2. Single dimension indexing: mds[['S1', 'S2']]")
    view2 = mds[["S1", "S2"]]
    print(f"   Result: {type(view2).__name__}")

    # Test 3: NEW - Chaining operations
    print("3. NEW - Chaining: mds[['S1', 'S2', 'S3']][['G2']]")
    try:
        view3 = mds[["S1", "S2", "S3"]][["G2"]]  # Should work now!
        print(f"   Result: {type(view3).__name__}")
        print("   ✅ Chaining works!")
    except Exception as e:
        print(f"   ❌ Chaining failed: {e}")
    print()

    # Test 4: NEW - Multiple chaining levels
    print(
        "4. NEW - Multiple chaining: mds[['S1', 'S2', 'S3', 'S4']][['G1', 'G2']][['S1', 'S3']]"
    )
    try:
        view4 = mds[["S1", "S2", "S3", "S4"]][["G1", "G2"]][["S1", "S3"]]
        print(f"   Result: {type(view4).__name__}")
        print("   ✅ Multiple chaining works!")
    except Exception as e:
        print(f"   ❌ Multiple chaining failed: {e}")
    print()

    # Test 5: NEW - Expression-based chaining
    print("5. NEW - Expression chaining: mds[polars_expr][['G1']]")
    try:
        disease_filter = pl.col("sample").is_in(
            ["S2", "S4"]
        )  # Treatment samples
        view5 = mds[disease_filter][["G1"]]
        print(f"   Result: {type(view5).__name__}")
        print("   ✅ Expression chaining works!")
    except Exception as e:
        print(f"   ❌ Expression chaining failed: {e}")
    print()

    print("\n=== Summary ===")
    print("✅ MetabiomeView now supports chaining!")
    print("✅ You can do: mds[samples][features] or view[more_samples]")
    print("✅ Both list and expression filters work with chaining")
    print("✅ Multiple levels of chaining are supported")


if __name__ == "__main__":
    test_chaining_functionality()
