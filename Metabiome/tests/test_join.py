#!/usr/bin/env python3
"""Test MetabiomeDataSpace.join() method functionality."""

from pathlib import Path

import pytest

import metabiome.io as mio


@pytest.fixture
def sample_space():
    """Load sample data for testing."""
    return mio.from_files(
        metadata_path=Path("data/input/metadata"),
        abundance_path=Path("data/input/RPKM.json"),
        taxonomy_path=Path("data/input/taxonomy.json"),
        functional_path=Path("data/input/FG.json"),
        sequences_path=Path("data/input/merged.fasta"),
        id_mapping_path=Path("data/input/id_mapping.tsv"),
    )


def test_join_dimensions_consistency(sample_space):
    """Test that join maintains consistent dimensions across data components."""
    space = sample_space

    # Get dimensions
    n_samples_abundance = space.abundance["sample"].n_unique()
    n_features_abundance = space.abundance["gc_id"].n_unique()
    n_samples_metadata = space.metadata["sample"].n_unique()
    n_features_annotation = space.annotation["gc_id"].n_unique()

    # Assert sample consistency
    assert n_samples_abundance == n_samples_metadata, (
        f"Sample mismatch: abundance ({n_samples_abundance}) != metadata ({n_samples_metadata})"
    )

    # Assert feature consistency
    assert n_features_abundance == n_features_annotation, (
        f"Feature mismatch: abundance ({n_features_abundance}) != annotation ({n_features_annotation})"
    )


def test_join_sample_overlap(sample_space):
    """Test that samples are properly aligned between abundance and metadata."""
    space = sample_space

    abundance_samples = set(space.abundance["sample"].unique().to_list())
    metadata_samples = set(space.metadata["sample"].unique().to_list())

    # Assert no orphaned samples
    assert abundance_samples == metadata_samples, (
        "Sample sets should be identical after join"
    )


def test_join_feature_overlap(sample_space):
    """Test that features are properly aligned between abundance and annotation."""
    space = sample_space

    abundance_features = set(space.abundance["gc_id"].unique().to_list())
    annotation_features = set(space.annotation["gc_id"].unique().to_list())

    # Assert no orphaned features
    assert abundance_features == annotation_features, (
        "Feature sets should be identical after join"
    )
