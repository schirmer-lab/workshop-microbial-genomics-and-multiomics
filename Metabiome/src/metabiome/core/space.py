"""
This module provides the main data structure for metabiome analysis, inspired by
AnnData's design but optimized for metagenomic data with lazy evaluation using Polars.
"""

from __future__ import annotations

import warnings
from collections.abc import Iterable
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING, Self

import polars as pl
import pyfaidx

from .matrix import SparseAbundanceMatrix

if TYPE_CHECKING:
    from ..annotations.catalog import GeneGroup
    from ..pl.plotting import PlottingAccessor
    from .filtering import FilterAccessor
    from .grouping import GroupByAccessor


@dataclass
class MetabiomeDataSpace:
    """
    Lazy-loading container for integrated metagenomic data analysis.

    This class provides a robust structure for
    handling observations (samples), variables (features), and the primary data matrix (X).

    Attributes
    ----------
    obs : polars.LazyFrame
        Sample metadata.
    var : polars.LazyFrame
        Feature annotations.
    X : SparseAbundanceMatrix
        The primary abundance data matrix.
    sequences : pyfaidx.Fasta, optional
        FASTA sequences associated with features.
    id_mapping : polars.LazyFrame, optional
        ID mapping information.
    uns : dict
        Unaffected annotations (miscellaneous data).
    _backing_store : str, optional
        Path to the backing store if data is disk-backed.
    obs_names : polars.Series
        Vector of sample IDs.
    var_names : polars.Series
        Vector of feature IDs.
    n_obs : int
        Number of observations (samples).
    n_vars : int
        Number of variables (features).
    shape : tuple[int, int]
        Shape of the data space (n_obs, n_vars).
    """

    # Internal, raw data attributes
    _obs: pl.LazyFrame
    _X: "SparseAbundanceMatrix"
    _var: pl.LazyFrame

    # Key for observation and variable columns
    obs_key: str = "sample"
    var_key: str = "gc_id"

    # Optional fields
    _sequences: pyfaidx.Fasta | None = None
    _id_mapping: pl.LazyFrame | None = None
    uns: dict = field(default_factory=dict)
    _backing_store: str | None = None
    _outdir: Path | None = field(default=None, repr=False)

    def _clear_cache(self, *cache_keys: str):
        """
        Clear specified keys from the instance's cache.

        Parameters
        ----------
        *cache_keys : str
            Variable length argument list of cache keys to clear.
        """
        for key in cache_keys:
            if key in self.__dict__:
                del self.__dict__[key]

    @classmethod
    def from_raw_data(
        cls,
        obs: pl.LazyFrame,
        abundance: pl.LazyFrame,
        taxonomy: pl.LazyFrame,
        functional: pl.LazyFrame,
        sequences: pyfaidx.Fasta | None = None,
        id_mapping: pl.LazyFrame | None = None,
        outdir: Path | str | None = None,
        obs_key: str = "sample",
        var_key: str = "gc_id",
        **kwargs,
    ) -> Self:
        """
        Create MetabiomeDataSpace from raw data that needs alignment.

        This method ensures all samples from obs are included in the abundance
        matrix, padding missing samples with zero abundances.

        Parameters
        ----------
        obs : polars.LazyFrame
            Sample metadata.
        abundance : polars.LazyFrame
            Gene abundance data in long format.
        taxonomy : polars.LazyFrame
            Taxonomy annotations.
        functional : polars.LazyFrame
            Functional group annotations.
        sequences : pyfaidx.Fasta, optional
            FASTA sequences.
        id_mapping : polars.LazyFrame, optional
            ID mapping information.
        outdir : Path | str, optional
            Output directory for results.
        obs_key : str, default "sample"
            Key for observation IDs.
        var_key : str, default "gc_id"
            Key for variable IDs.
        **kwargs
            Additional keyword arguments to be stored in `uns`.

        Returns
        -------
        MetabiomeDataSpace
            A new MetabiomeDataSpace instance.
        """

        obs_df = obs.collect()
        abundance_df = abundance.collect()
        var_df = taxonomy.join(
            functional, on=var_key, how="outer_coalesce"
        ).collect()

        all_obs_names = (
            obs_df.select(obs_key)
            .filter(pl.col(obs_key).is_not_null())
            .unique()
            .sort(obs_key)[obs_key]
            .to_list()
        )
        all_var_names = (
            var_df.select(var_key).unique().sort(var_key)[var_key].to_list()
        )

        missing = set(all_obs_names) - set(
            abundance_df.select(obs_key).unique()[obs_key].to_list()
        )

        abundance_df = abundance_df.filter(pl.col(obs_key).is_in(all_obs_names))

        # Add zero abundance rows for missing samples using cross join
        if missing:
            missing_df = (
                pl.DataFrame({obs_key: list(missing)})
                .join(pl.DataFrame({var_key: all_var_names}), how="cross")
                .with_columns(
                    abundance=pl.lit(
                        0.0, dtype=abundance_df.schema["abundance"]
                    )
                )
                .select(abundance_df.columns)  # Ensure column order matches
            )
            abundance_df = pl.concat([abundance_df, missing_df])

        var = taxonomy.join(functional, on=var_key, how="outer_coalesce")

        # Create instance
        instance = cls(
            _obs=obs,
            _X=SparseAbundanceMatrix.from_polars(
                abundance_df,
                obs_col=obs_key,
                var_col=var_key,
            ),
            _var=var,
            obs_key=obs_key,
            var_key=var_key,
            _sequences=sequences,
            _id_mapping=id_mapping,
            _outdir=Path(outdir) if outdir else None,
            uns=kwargs,
        )
        return instance

    @classmethod
    def from_filtered_data(
        cls,
        obs: pl.LazyFrame,
        X: "SparseAbundanceMatrix",
        var: pl.LazyFrame,
        sequences: pyfaidx.Fasta | None = None,
        id_mapping: pl.LazyFrame | None = None,
        outdir: Path | str | None = None,
        obs_key: str = "sample",
        var_key: str = "gc_id",
        **kwargs,
    ) -> Self:
        """
        Create MetabiomeDataSpace from already-filtered/aligned data.

        Parameters
        ----------
        obs : polars.LazyFrame
            Sample metadata.
        X : SparseAbundanceMatrix
            The primary abundance data matrix.
        var : polars.LazyFrame
            Feature annotations.
        sequences : pyfaidx.Fasta, optional
            FASTA sequences.
        id_mapping : polars.LazyFrame, optional
            ID mapping information.
        outdir : Path | str, optional
            Output directory for results.
        **kwargs
            Additional keyword arguments to be stored in `uns`.

        Returns
        -------
        MetabiomeDataSpace
            A new MetabiomeDataSpace instance.
        """
        instance = cls(
            _obs=obs,
            _X=X,
            _var=var,
            obs_key=obs_key,
            var_key=var_key,
            _sequences=sequences,
            _id_mapping=id_mapping,
            _outdir=Path(outdir) if outdir else None,
            uns=kwargs,
        )

        return instance

    def collect(self) -> Self:
        """
        Materialize all LazyFrames to DataFrames.

        This method eagerly evaluates all lazy Polars DataFrames within the
        MetabiomeDataSpace, converting them into in-memory DataFrames.

        Returns
        -------
        MetabiomeDataSpace
            The MetabiomeDataSpace instance with materialized DataFrames.
        """
        self._obs = self._obs.collect()
        self._var = self._var.collect()
        if self._id_mapping is not None:
            self._id_mapping = self._id_mapping.collect()
        return self

    def lazy(self) -> Self:
        """
        Convert all DataFrames back to LazyFrames.

        This method converts all in-memory Polars DataFrames within the
        MetabiomeDataSpace back into lazy Polars LazyFrames, enabling lazy evaluation.

        Returns
        -------
        MetabiomeDataSpace
            The MetabiomeDataSpace instance with lazy DataFrames.
        """
        self._obs = self._obs.lazy()
        self._var = self._var.lazy()
        if self._id_mapping is not None:
            self._id_mapping = self._id_mapping.lazy()
        return self

    def __getitem__(
        self,
        index: tuple | str | Iterable[str] | pl.Expr,
    ) -> Self:
        """Filter the data space using label-based or expression-based indexing.

        This method allows for powerful and flexible subsetting of the data
        space along one or both axes (observations and variables).

        Parameters
        ----------
        index : tuple, str, list[str], or polars.Expr
            The slicing key. This can be one of the following:
            - A tuple `(obs_idx, var_idx)` for filtering both axes.
            - A single indexer for filtering only observations (rows).

            The indexers for each axis (`obs_idx`, `var_idx`) can be:
            - A `polars.Expr` for complex, conditional filtering.
            - A string (e.g., "sample_1") for selecting a single item by its ID.
            - An iterable of strings (e.g., ["sample_1", "sample_5"]) for
              selecting multiple items by their IDs.
            - A slice (e.g., `slice(None)` or `:`) to select all items.

        Returns
        -------
        MetabiomeDataSpace
            A new, filtered `MetabiomeDataSpace` instance.

        Examples
        --------
        >>> # Select a single sample by its ID
        >>> mds["sample_001", :]
        >>>
        >>> # Select multiple features by a list of IDs
        >>> mds[:, ["gene_A", "gene_B"]]
        >>>
        >>> # Filter samples based on a metadata condition
        >>> mds[pl.col("age") > 50, :]
        >>>
        >>> # Combine filters on both axes
        >>> mds[
        ...     pl.col("metadata.disease") == "IBD",
        ...     pl.col("annotation.pathway") == "Glycolysis",
        ... ]
        """
        if not isinstance(index, tuple):
            index = (index, slice(None))

        obs_idx, var_idx = index

        new_obs, new_var, new_id_mapping = (
            self._obs,
            self._var,
            self._id_mapping,
        )

        if not (isinstance(obs_idx, slice) and obs_idx == slice(None)):
            if isinstance(obs_idx, pl.Expr):
                filtered_obs = self._obs.filter(obs_idx)

                new_obs = filtered_obs

                obs_map = pl.LazyFrame(
                    {self.obs_key: list(self._X.obs_names)}
                ).with_row_count("row_idx")

                matched = (
                    filtered_obs.join(obs_map, on=self.obs_key, how="inner")
                    .select([self.obs_key, "row_idx"])
                    .sort("row_idx")
                    .collect()
                )

                obs_idx = matched["row_idx"].to_list()

                requested_samples = (
                    filtered_obs.select(self.obs_key)
                    .collect()[self.obs_key]
                    .to_list()
                )

                dropped = len(requested_samples) - len(matched)
                if dropped > 0:
                    warnings.warn(
                        f"{dropped} filtered samples were not present in the matrix and were dropped"
                    )

            else:
                obs_idx = [obs_idx] if isinstance(obs_idx, str) else obs_idx
                new_obs = self._obs.filter(pl.col(self.obs_key).is_in(obs_idx))

        if not (isinstance(var_idx, slice) and var_idx == slice(None)):
            if isinstance(var_idx, pl.Expr):
                filtered_var = self._var.filter(var_idx)

                new_var = filtered_var

                var_map = pl.LazyFrame(
                    {self.var_key: list(self._X.var_names)}
                ).with_row_count("col_idx")

                matched = (
                    filtered_var.join(var_map, on=self.var_key, how="inner")
                    .select([self.var_key, "col_idx"])
                    .sort("col_idx")
                    .collect()
                )

                var_idx = matched[self.var_key].to_list()

                requested_gc_ids = (
                    filtered_var.select(self.var_key)
                    .collect()[self.var_key]
                    .to_list()
                )
                dropped = len(requested_gc_ids) - len(matched)
                if dropped > 0:
                    warnings.warn(
                        f"{dropped} filtered features were not present in the matrix and were dropped"
                    )
            else:
                var_idx = [var_idx] if isinstance(var_idx, str) else var_idx
                new_var = self._var.filter(pl.col(self.var_key).is_in(var_idx))

            if new_id_mapping is not None:
                new_id_mapping = new_id_mapping.filter(
                    pl.col(self.var_key).is_in(var_idx)
                )

        new_X = self._X[obs_idx, var_idx]

        return self.from_filtered_data(
            obs=new_obs,
            X=new_X,
            var=new_var,
            sequences=self._sequences,
            id_mapping=new_id_mapping,
            uns=self.uns,
            obs_key=self.obs_key,
            var_key=self.var_key,
        )

    def __str__(self) -> str:
        """
        Return a string representation of the MetabiomeDataSpace object.

        Returns
        -------
        str
            A string summarizing the object's dimensions and key attributes.
        """
        n_obs, n_vars = self.shape
        msg = [
            f"MetabiomeDataSpace object with {n_obs} obs and {n_vars} vars",
            f"  obs: {self._obs.columns}",
            f"  var: {self._var.columns}",
            "  X: stored in sparse format",
        ]
        return "\n".join(msg)

    def __repr__(self) -> str:
        """
        Return a detailed string representation of the MetabiomeDataSpace object.

        Returns
        -------
        str
            A detailed string representation including dimensions and types of attributes.
        """
        n_obs, n_vars = self.shape
        msg = [f"MetabiomeDataSpace object ({n_obs} obs \u00d7 {n_vars} vars)"]
        for name in ["obs", "X", "var", "sequences", "id_mapping"]:
            value = getattr(self, f"_{name}")
            info = f" (type: {type(value).__name__})"
            msg.append(f"  {name}: {info}")
        return "\n".join(msg)

    def copy(self) -> Self:
        """
        Create a deep copy of the MetabiomeDataSpace object.

        Returns
        -------
        MetabiomeDataSpace
            A new MetabiomeDataSpace instance that is a deep copy of the original.
        """
        from copy import deepcopy

        return self.from_filtered_data(
            obs=deepcopy(self._obs),
            X=deepcopy(self._X),
            var=deepcopy(self._var),
            sequences=deepcopy(self._sequences),
            id_mapping=deepcopy(self._id_mapping),
            uns=deepcopy(self.uns),
            obs_key=self.obs_key,
            var_key=self.var_key,
        )

    def to_abundance_matrix(self, wide: bool = True, sparse: bool = False):
        """
        Convert the abundance data to a Polars DataFrame or SparseAbundanceMatrix.

        Parameters
        ----------
        wide : bool, default True
            If True, return a wide-format DataFrame (samples as rows, features as columns).
            If False, return a long-format DataFrame (sample, gc_id, abundance columns).
        sparse : bool, default False
            If True, return the SparseAbundanceMatrix object directly.

        Returns
        -------
        polars.LazyFrame or SparseAbundanceMatrix
            The abundance data in the specified format. Note: `to_wide()` and
            `to_long()` return a lazy Polars frame (`pl.LazyFrame`); call
            `.collect()` when you need an in-memory `pl.DataFrame`.
        """
        if sparse:
            return self.X
        return self.X.to_wide() if wide else self.X.to_long()

    def save(self, store_path: str | Path, overwrite: bool = False):
        """Save the MetabiomeDataSpace to a directory-based store.

        This method uses a directory-based format that is optimized for
        performance and lazy loading. Each component of the data space is
        saved to a separate file in its most efficient format (e.g.,
        Parquet for tables, Zarr for sparse matrices).

        Parameters
        ----------
        store_path : str or pathlib.Path
            Path to the directory where the data space will be saved.
        overwrite : bool, default False
            If True, any existing directory at the specified path will be
            overwritten.
        """
        from ..io.writers import write

        write(self, store_path, overwrite=overwrite)

    @classmethod
    def read(cls, store_path: str | Path) -> Self:
        """Load a MetabiomeDataSpace from a directory-based store.

        Parameters
        ----------
        store_path : str or pathlib.Path
            Path to the directory from which to load the data space.

        Returns
        -------
        MetabiomeDataSpace
            The loaded MetabiomeDataSpace object.
        """
        from ..io.readers import read

        return read(store_path)

    # --- Accessors and Properties ---
    @property
    def groupby(self) -> "GroupByAccessor":
        """
        Accessor for grouping operations.

        Returns
        -------
        GroupByAccessor
            An accessor object providing methods for grouping observations and variables.

        Examples
        --------
        >>> # Group by a single observation column
        >>> mds.groupby.obs("disease_group")

        >>> # Group by multiple feature columns
        >>> mds.groupby.var(["pfam_domain", "kegg_pathway"])

        >>> # Cross-dimensional grouping
        >>> mds.groupby(obs="disease_group", var="pfam_domain")
        """
        from .grouping import GroupByAccessor

        return GroupByAccessor(self)

    @property
    def filter(self) -> "FilterAccessor":
        """
        Accessor for filtering operations.

        Returns
        -------
        FilterAccessor
            An accessor object providing methods for filtering observations and variables.

        Examples
        --------
        >>> mds.filter.obs(pl.col("disease") == "IBD")
        >>> mds.filter.var(pl.col("gene_length") > 1000)
        >>> mds.filter.X(by="var", pl.col("prevalence") > 0.1)
        """
        from .filtering import FilterAccessor

        return FilterAccessor(self)

    @property
    def pl(self) -> "PlottingAccessor":
        """
        Accessor for plotting functions.

        Returns
        -------
        PlottingAccessor
            An accessor object providing methods for generating various plots.

        Examples
        --------
        >>> mds.pl.sankey(hierarchy_cols=["domain", "phylum", "species"])
        >>> mds.pl.boxplot(
        ...     feature_name="Escherichia coli", x_axis_col="disease_group"
        ... )
        """
        from ..pl.plotting import PlottingAccessor

        return PlottingAccessor(self)

    @property
    def genes(self) -> "GeneGroup":
        """
        Access the gene group analyzer.

        Returns
        -------
        GeneGroup
            An accessor object providing methods for analyzing groups of genes.
        """
        from ..annotations.catalog import GeneGroup

        return GeneGroup(self)

    @cached_property
    def index_manager(self):
        """Construct a cached IndexManager from the space's `_id_mapping` if present.

        Returns `None` when `_id_mapping` is not provided.
        """
        if self._id_mapping is None:
            return None

        from .indexing import IndexManager

        return IndexManager(self._id_mapping)

    @cached_property
    def obs(self) -> pl.DataFrame:
        """
        Sample metadata as a Polars DataFrame (cached).

        Returns
        -------
        polars.DataFrame
            A DataFrame containing sample-related metadata.
        """
        return self._obs.collect()

    @property
    def X(self) -> "SparseAbundanceMatrix":
        """
        The primary abundance data matrix (not cached).

        Returns
        -------
        SparseAbundanceMatrix
            The sparse abundance matrix containing gene counts or similar data.
        """
        return self._X

    @cached_property
    def var(self) -> pl.DataFrame:
        """
        Feature annotations as a Polars DataFrame (cached).

        Returns
        -------
        polars.DataFrame
            A DataFrame containing feature-related annotations.
        """
        return self._var.collect()

    @property
    def sequences(self) -> pyfaidx.Fasta | None:
        """
        FASTA sequences associated with features.

        Returns
        -------
        pyfaidx.Fasta or None
            A pyfaidx.Fasta object if sequences are available, otherwise None.
        """
        return self._sequences

    @property
    def id_mapping(self) -> pl.DataFrame | None:
        """
        ID mapping information as a Polars DataFrame.

        Returns
        -------
        polars.DataFrame or None
            A DataFrame containing ID mapping information if available, otherwise None.
        """
        return (
            self._id_mapping.collect() if self._id_mapping is not None else None
        )

    @cached_property
    def obs_names(self) -> pl.Series:
        """
        Vector of sample IDs (cached).

        Returns
        -------
        polars.Series
            A Series containing the unique sample identifiers.
        """
        return self.obs[self.obs_key]

    @cached_property
    def var_names(self) -> pl.Series:
        """
        Vector of feature IDs (cached).

        Returns
        -------
        polars.Series
            A Series containing the unique feature identifiers.
        """
        return self.var[self.var_key]

    @cached_property
    def n_obs(self) -> int:
        """
        Number of observations (samples) (cached).

        Returns
        -------
        int
            The number of observations.
        """
        return len(self.X.obs_names)

    @cached_property
    def n_vars(self) -> int:
        """
        Number of variables (features) (cached).

        Returns
        -------
        int
            The number of variables.
        """
        return self.var.height

    @cached_property
    def shape(self) -> tuple[int, int]:
        """
        Shape of the data space (n_obs, n_vars) (cached).

        Returns
        -------
        tuple[int, int]
            A tuple representing the number of observations and variables.
        """
        return (len(self.X.obs_names), len(self.X.var_names))

    @property
    def outdir(self) -> Path:
        """
        Output directory for storing results.

        Returns
        -------
        Path
            The path to the output directory.
        """
        return self._outdir if self._outdir else Path.cwd()

    @outdir.setter
    def outdir(self, value: str | Path):
        """
        Set the output directory.

        Parameters
        ----------
        value : str or Path
            The path to the output directory.
        """
        self._outdir = Path(value)

    @property
    def memory_usage(self) -> dict:
        """
        Get memory usage statistics for the data space.

        Returns
        -------
        dict
            Memory usage breakdown by component
        """
        usage = {}

        attr_map = {
            "_obs": "obs",
            "_X": "X",
            "_var": "var",
            "_id_mapping": "id_mapping",
        }

        for internal_attr, display_name in attr_map.items():
            attr = getattr(self, internal_attr)
            if attr is not None:
                if isinstance(attr, pl.LazyFrame):
                    usage[display_name] = "lazy (not materialized)"
                elif isinstance(attr, pl.DataFrame):
                    usage[display_name] = f"{attr.estimated_size('mb'):.2f} MB"
                elif isinstance(attr, SparseAbundanceMatrix):
                    usage[display_name] = (
                        f"{attr.data.data.nbytes / 1e6:.2f} MB (sparse)"
                    )
                else:
                    usage[display_name] = "unknown type"
            else:
                usage[display_name] = "None"

        if self._sequences is not None:
            usage["sequences"] = f"FASTA ({len(self._sequences)} sequences)"

        return usage

    def memory_info(self) -> None:
        """Print detailed memory usage information."""
        print("MetabiomeDataSpace Memory Usage:")
        print("=" * 40)

        usage = self.memory_usage
        for component, size in usage.items():
            print(f"{component:12}: {size}")

        print("=" * 40)
        total_lazy = sum(1 for v in usage.values() if "lazy" in str(v))
        total_materialized = sum(1 for v in usage.values() if "MB" in str(v))
        print(f"Lazy components: {total_lazy}")
        print(f"Materialized components: {total_materialized}")
