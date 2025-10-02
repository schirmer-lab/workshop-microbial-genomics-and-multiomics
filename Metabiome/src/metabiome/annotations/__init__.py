"""
Annotation and catalog management modules.

This package contains modules for processing raw metagenomic data,
building gene catalogs, clustering sequences, and annotating with
taxonomy and functional information.
"""

from .catalog import GroupAccessor, GeneGroup, ProteinGroup
from .taxonomy import (
    NCBI,
    Taxonomy,
    build_lineage,
    get_taxonomy_from_json,
    merge_taxa,
    parse_ncbi_taxonomy,
    process_gtdb_annotations,
    process_metaphlan_annotations,
)

__all__ = [
    "GroupAccessor",
    "GeneGroup",
    "ProteinGroup",
    "Taxonomy",
    "NCBI",
    "parse_ncbi_taxonomy",
    "build_lineage",
    "process_metaphlan_annotations",
    "process_gtdb_annotations",
    "merge_taxa",
    "get_taxonomy_from_json",
]
