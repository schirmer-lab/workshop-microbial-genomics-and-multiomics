"""
Factory method for creating MetabiomeDataSpace instances from various raw file sources.
"""

import json
from pathlib import Path
from typing import TYPE_CHECKING

import polars as pl
import pyfaidx
import scipy.sparse as sp
import zarr

if TYPE_CHECKING:
    from ..core.space import MetabiomeDataSpace

from ..core.matrix import SparseAbundanceMatrix
from .parsers import (
    BaseParser,
    FunctionalGroupParser,
    GeneAbundanceParser,
    IDMappingParser,
    MetadataParser,
    SequenceParser,
    TaxonomyParser,
)


def from_files(
    obs: str | Path | BaseParser,
    abundance: str | Path | BaseParser,
    taxonomy: str | Path | BaseParser | None = None,
    functional: str | Path | BaseParser | None = None,
    sequences: str | Path | BaseParser | None = None,
    id_mapping: str | Path | BaseParser | None = None,
    **parser_kwargs: dict,
) -> "MetabiomeDataSpace":
    """
    Create MetabiomeDataSpace from various data sources.

    This is the primary factory method for creating a data space from
    standard metagenomic data files or custom user-provided parsers.

    Parameters
    ----------
    obs : str, Path, or BaseParser
        Path to sample metadata file or a pre-initialized parser object.
    abundance : str, Path, or BaseParser
        Path to gene abundance file or a pre-initialized parser object.
    taxonomy : str, Path, BaseParser, optional
        Path to taxonomy annotations file or a parser object.
    functional : str, Path, BaseParser, optional
        Path to functional group annotations file or a parser object.
    sequences : str, Path, BaseParser, optional
        Path to FASTA sequences file or a parser object.
    id_mapping : str, Path, BaseParser, optional
        Path to ID mapping file or a parser object.
    **parser_kwargs
        Additional keyword arguments passed to the default parsers if paths are provided.

    Returns
    -------
    MetabiomeDataSpace
        A configured MetabiomeDataSpace instance with lazy-loaded data.
    """
    from ..core.space import MetabiomeDataSpace

    def _resolve_parser(
        data_source: str | Path | BaseParser | None,
        default_parser: type[BaseParser],
    ) -> BaseParser | None:
        if data_source is None:
            return None
        if isinstance(data_source, (str, Path)):
            return default_parser(data_source, **parser_kwargs)
        return data_source

    # Resolve all inputs to parser instances
    obs_parser = _resolve_parser(obs, MetadataParser)
    abundance_parser = _resolve_parser(abundance, GeneAbundanceParser)
    taxonomy_parser = _resolve_parser(taxonomy, TaxonomyParser)
    functional_parser = _resolve_parser(functional, FunctionalGroupParser)
    sequences_parser = _resolve_parser(sequences, SequenceParser)
    id_mapping_parser = _resolve_parser(id_mapping, IDMappingParser)

    data_components = {
        "obs": obs_parser.data if obs_parser else None,
        "abundance": abundance_parser.data if abundance_parser else None,
        "taxonomy": taxonomy_parser.data if taxonomy_parser else None,
        "functional": functional_parser.data if functional_parser else None,
        "sequences": sequences_parser.data if sequences_parser else None,
        "id_mapping": id_mapping_parser.data if id_mapping_parser else None,
    }

    return MetabiomeDataSpace.from_raw_data(**data_components, **parser_kwargs)


def from_space(store_path: str | Path) -> "MetabiomeDataSpace":
    """Load a MetabiomeDataSpace from a directory-based store."""
    from ..core.space import MetabiomeDataSpace

    path = Path(store_path)
    if not path.is_dir():
        raise FileNotFoundError(
            f"Store path '{path}' not found or is not a directory."
        )

    # Read metadata
    obs = pl.scan_parquet(path / "obs.parquet")
    var = pl.scan_parquet(path / "var.parquet")

    # Read abundance matrix from Zarr
    zarr_path = path / "X"
    root = zarr.open_group(store=str(zarr_path), mode="r")

    data = root["data"][:]
    indices = root["indices"][:]
    indptr = root["indptr"][:]
    shape = tuple(root.attrs["shape"])
    obs_names = list(root.attrs["obs_names"])
    var_names = list(root.attrs["var_names"])

    csr_matrix = sp.csr_matrix((data, indices, indptr), shape=shape)
    X = SparseAbundanceMatrix(
        data=csr_matrix, obs_names=obs_names, var_names=var_names
    )

    # Read optional components
    sequences = None
    if (path / "sequences.fa").exists():
        sequences = pyfaidx.Fasta(str(path / "sequences.fa"))

    id_mapping = None
    if (path / "id_mapping.parquet").exists():
        id_mapping = pl.scan_parquet(path / "id_mapping.parquet")

    uns = {}
    if (path / "uns.json").exists():
        with (path / "uns.json").open("r") as f:
            uns = json.load(f)

    return MetabiomeDataSpace.from_filtered_data(
        obs=obs,
        X=X,
        var=var,
        sequences=sequences,
        id_mapping=id_mapping,
        **uns,
    )
