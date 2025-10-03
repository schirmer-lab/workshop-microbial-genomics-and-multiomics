"""
Input/output module for the metabiome package.

This module provides functionality for loading and saving MetabiomeDataSpace
objects, as well as parsing raw data from various file formats.
"""

from .backing_store import BackingStore
from .parsers import (
    BaseParser,
    FunctionalGroupParser,
    GeneAbundanceParser,
    IDMappingParser,
    MetadataParser,
    SequenceParser,
    TaxonomyParser,
)
from .readers import from_files, from_space
from .writers import write

__all__ = [
    "from_files",
    "from_space",
    "write",
    "BaseParser",
    "GeneAbundanceParser",
    "FunctionalGroupParser",
    "TaxonomyParser",
    "SequenceParser",
    "IDMappingParser",
    "MetadataParser",
    "BackingStore",
]
