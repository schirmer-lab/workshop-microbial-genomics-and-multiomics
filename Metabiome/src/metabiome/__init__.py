"""
Metabiome: High-performance metagenomics data container and analysis toolkit.

A comprehensive Python package for handling large-scale metagenomic cohort studies
with performance-optimized data structures using Zarr arrays and Polars DataFrames.
"""

import polars

from . import (
    analysis,
    annotations,
    cloud,
    core,
    io,
    optimized,
    pl,
    preprocessing,
    utils,
)
from .core.space import MetabiomeDataSpace

polars.enable_string_cache()

__version__ = "0.1.0"

__all__ = [
    "MetabiomeDataSpace",
    "analysis",
    "annotations",
    "cloud",
    "core",
    "io",
    "optimized",
    "preprocessing",
    "utils",
    "pl",
]
