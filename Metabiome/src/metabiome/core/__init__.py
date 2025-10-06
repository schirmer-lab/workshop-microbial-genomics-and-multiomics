"""
Core module for the metabiome package.

This module provides the fundamental data structures and storage backends
for metagenomic data management.
"""

from .grouping import GroupedMetabiomeDataSpace
from .indexing import IndexManager
from .matrix import SparseAbundanceMatrix
from .operations import (
    concat_spaces,
)
from .space import MetabiomeDataSpace

__all__ = [
    "MetabiomeDataSpace",
    "GroupedMetabiomeDataSpace",
    "SparseAbundanceMatrix",
    "concat_spaces",
    "IndexManager",
]
