"""
Matrix operations and sparse matrix support for MetabiomeDataSpace.

Optimized for metagenomic abundance matrices using Polars and scipy.sparse.
"""

import numpy as np
import polars as pl
import scipy.sparse as sp


class SparseAbundanceMatrix:
    """
    Sparse matrix wrapper for abundance data with metadata alignment.

    Integrates with Polars for efficient metadata operations while
    providing scipy.sparse functionality for numerical computations.
    """

    def __init__(
        self,
        data: sp.csr_matrix,
        obs_names: list[str],
        var_names: list[str],
        obs_col: str = "sample",
        var_col: str = "gc_id",
    ):
        """
        Initialize sparse abundance matrix.

        Parameters
        ----------
        data : sp.csr_matrix
            Sparse matrix in CSR format (samples × features)
        obs_names : list[str]
            Sample identifiers corresponding to matrix rows
        var_names : list[str]
            Feature identifiers corresponding to matrix columns
        """
        self.data = data
        self.obs_names = obs_names
        self.var_names = var_names
        self.obs_col = obs_col
        self.var_col = var_col

        # Validate dimensions
        if data.shape[0] != len(obs_names):
            raise ValueError(
                f"Matrix rows ({data.shape[0]}) != sample count ({len(obs_names)})"
            )
        if data.shape[1] != len(var_names):
            raise ValueError(
                f"Matrix cols ({data.shape[1]}) != feature count ({len(var_names)})"
            )

    @classmethod
    def from_polars(
        cls,
        df: pl.DataFrame | pl.LazyFrame,
        obs_col: str = "sample",
        var_col: str = "gc_id",
        value_col: str = "abundance",
    ) -> "SparseAbundanceMatrix":
        """
        Create sparse matrix from long-format Polars DataFrame using an optimized,
        vectorized approach.

        Parameters
        ----------
        df : pl.DataFrame | pl.LazyFrame
            Long-format DataFrame with sample, feature, value columns
        obs_col : str, default "sample"
            Column name for sample identifiers
        var_col : str, default "gc_id"
            Column name for feature identifiers
        value_col : str, default "abundance"
            Column name for abundance values

        Returns
        -------
        SparseAbundanceMatrix
            Sparse matrix representation
        """
        df = (
            df.select([obs_col, var_col, value_col]).collect()
            if isinstance(df, pl.LazyFrame)
            else df
        )

        # Filter out rows with null values in the key columns to avoid None in names
        df = df.filter(
            pl.col(obs_col).is_not_null() & pl.col(var_col).is_not_null()
        )

        # Get unique, sorted sample and feature IDs
        obs_names = df.select(obs_col).unique().sort(obs_col)[obs_col].to_list()
        var_names = df.select(var_col).unique().sort(var_col)[var_col].to_list()

        # Create mapping dictionaries for fast lookups
        obs_to_idx = {obs: idx for idx, obs in enumerate(obs_names)}
        var_to_idx = {var: idx for idx, var in enumerate(var_names)}

        # Vectorized creation of row and column indices
        df_with_indices = df.with_columns(
            pl.col(obs_col).replace(obs_to_idx).alias("row_idx"),
            pl.col(var_col).replace(var_to_idx).alias("col_idx"),
        )

        # Extract arrays for sparse matrix construction
        rows = df_with_indices["row_idx"].to_numpy()
        cols = df_with_indices["col_idx"].to_numpy()
        values = df_with_indices[value_col].to_numpy()

        # Note that Scipy's csr_matrix constructor automatically sums values for duplicate
        # (row, col) coordinates, so an explicit aggregation in Polars is not needed.
        sparse_data = sp.csr_matrix(
            (values, (rows, cols)), shape=(len(obs_names), len(var_names))
        )

        return cls(sparse_data, obs_names, var_names, obs_col, var_col)

    def to_long(self, include_zeros: bool = False) -> pl.LazyFrame:
        """
        Convert back to long-format Polars DataFrame.

        Parameters
        ----------
        include_zeros : bool, default False
            Whether to include zero values in output

        Returns
        -------
        pl.DataFrame
            Long-format DataFrame
        """
        if include_zeros:
            # Convert to dense and include all values
            dense_data = self.data.toarray()
            rows, cols = np.meshgrid(
                np.arange(len(self.obs_names)),
                np.arange(len(self.var_names)),
                indexing="ij",
            )

            obs_names_expanded = [self.obs_names[i] for i in rows.flatten()]
            var_names_expanded = [self.var_names[i] for i in cols.flatten()]
            values_expanded = dense_data.flatten()

        else:
            # Only include non-zero values
            coo = self.data.tocoo()
            rows, cols, values = coo.row, coo.col, coo.data
            obs_names_expanded = [self.obs_names[i] for i in rows]
            var_names_expanded = [self.var_names[i] for i in cols]
            values_expanded = values

        return pl.LazyFrame(
            {
                self.obs_col: obs_names_expanded,
                self.var_col: var_names_expanded,
                "abundance": values_expanded,
            }
        )

    def to_wide(self) -> pl.LazyFrame:
        """
        Convert to wide-format Polars DataFrame (samples × features).

        Returns
        -------
        pl.DataFrame
            Wide-format DataFrame with samples as rows, features as columns
        """
        dense_data = self.data.toarray()

        df_dict = {self.obs_col: pl.Series(self.obs_col, self.obs_names)}
        for i, var_name in enumerate(self.var_names):
            df_dict[var_name] = pl.Series(var_name, dense_data[:, i])

        return pl.LazyFrame(df_dict)

    def __getitem__(self, index: tuple) -> "SparseAbundanceMatrix":
        """
        Enable 2D slicing using labels (obs_names, var_names).

        Parameters
        ----------
        index : tuple
            A tuple of (row_indexer, col_indexer) where each indexer can be
            a string, a list of strings, or a slice.

        Returns
        -------
        SparseAbundanceMatrix
            A new, sliced sparse abundance matrix.
        """
        if not isinstance(index, tuple) or len(index) != 2:
            raise ValueError("Indexing must be a 2-tuple of (rows, cols)")

        row_idx, col_idx = index

        def _to_positions(indexer, names, axis_label: str) -> list[int]:
            """Convert a row/col indexer to integer positions.

            Fast, readable checks in order: slice, str, int, then iterable.
            """
            # full-slice case
            if isinstance(indexer, slice):
                if indexer == slice(None):
                    return list(range(len(names)))
                raise ValueError(
                    f"Positional slicing with a slice is not supported for {axis_label}. Use IDs, lists of IDs, or lists of integer positions."
                )

            # single ID
            if isinstance(indexer, str):
                pos_map = {name: i for i, name in enumerate(names)}
                return [pos_map[indexer]] if indexer in pos_map else []

            # single integer position
            if isinstance(indexer, int):
                return [indexer]

            try:
                idx_list = (
                    indexer
                    if isinstance(indexer, (list, tuple))
                    else list(indexer)
                )
            except TypeError:
                raise ValueError(
                    f"Unsupported indexer type for {axis_label}: {type(indexer)}"
                )

            if not idx_list:
                return []

            first = idx_list[0]
            if isinstance(first, int):
                return list(idx_list)

            # treat as list of IDs
            pos_map = {name: i for i, name in enumerate(names)}
            return [pos_map[x] for x in idx_list if x in pos_map]

        obs_indices = _to_positions(row_idx, self.obs_names, "rows")
        feature_indices = _to_positions(col_idx, self.var_names, "cols")

        # Guard empty selections to produce an empty sparse matrix
        if len(obs_indices) == 0 or len(feature_indices) == 0:
            new_data = sp.csr_matrix((len(obs_indices), len(feature_indices)))
        else:
            new_data = self.data[obs_indices, :][:, feature_indices]

        new_obs_names = [self.obs_names[i] for i in obs_indices]
        new_var_names = [self.var_names[i] for i in feature_indices]

        return SparseAbundanceMatrix(
            data=new_data,
            obs_names=new_obs_names,
            var_names=new_var_names,
            obs_col=self.obs_col,
            var_col=self.var_col,
        )

    def normalize(self, method: str = "total_sum") -> "SparseAbundanceMatrix":
        """
        Normalize abundance data.

        Parameters
        ----------
        method : str, default "total_sum"
            Normalization method ("total_sum", "max", "l2")

        Returns
        -------
        SparseAbundanceMatrix
            Normalized matrix
        """
        if method == "total_sum":
            # Divide each sample by its total abundance
            row_sums = np.array(self.data.sum(axis=1)).flatten()
            row_sums[row_sums == 0] = 1  # Avoid division by zero
            normalized_data = self.data.multiply(1 / row_sums[:, np.newaxis])

        elif method == "max":
            # Divide by maximum value in each sample
            row_maxs = np.array(self.data.max(axis=1).toarray()).flatten()
            row_maxs[row_maxs == 0] = 1
            normalized_data = self.data.multiply(1 / row_maxs[:, np.newaxis])

        elif method == "l2":
            # L2 normalization
            from sklearn.preprocessing import normalize

            normalized_data = normalize(self.data, norm="l2", axis=1)

        else:
            raise ValueError(f"Unknown normalization method: {method}")

        return SparseAbundanceMatrix(
            normalized_data,
            self.obs_names,
            self.var_names,
            obs_col=self.obs_col,
            var_col=self.var_col,
        )

    def get_feature_stats(self) -> pl.DataFrame:
        """
        Calculate feature-level statistics.

        Returns
        -------
        pl.DataFrame
            Feature statistics (prevalence, mean, std, etc.)
        """
        prevalence = np.array((self.data > 0).sum(axis=0)).flatten()
        means = np.array(self.data.mean(axis=0)).flatten()
        stds = np.sqrt(
            np.array(self.data.power(2).mean(axis=0)).flatten() - means**2
        )
        maxs = np.array(self.data.max(axis=0).toarray()).flatten()

        stats_df = pl.DataFrame(
            {
                self.var_col: self.var_names,
                "prevalence": prevalence,
                "mean_abundance": means,
                "std_abundance": stds,
                "max_abundance": maxs,
                "prevalence_pct": (prevalence / len(self.obs_names)) * 100,
            }
        )

        return stats_df

    def get_sample_stats(self) -> pl.DataFrame:
        """
        Calculate sample-level statistics.

        Returns
        -------
        pl.DataFrame
            Sample statistics (total abundance, feature count, etc.)
        """
        total_abundance = np.array(self.data.sum(axis=1)).flatten()
        feature_count = np.array((self.data > 0).sum(axis=1)).flatten()
        max_abundance = np.array(self.data.max(axis=1).toarray()).flatten()

        stats_df = pl.DataFrame(
            {
                self.obs_col: self.obs_names,
                "total_abundance": total_abundance,
                "feature_count": feature_count,
                "max_abundance": max_abundance,
                "mean_abundance": total_abundance / feature_count,
            }
        )

        return stats_df

    @property
    def shape(self) -> tuple[int, int]:
        """Get matrix shape (samples, features)."""
        return self.data.shape

    @property
    def nnz(self) -> int:
        """Get number of non-zero elements."""
        return self.data.nnz

    @property
    def density(self) -> float:
        """Get matrix density (fraction of non-zero elements)."""
        return self.nnz / (self.shape[0] * self.shape[1])

    def __str__(self) -> str:
        """String representation."""
        return (
            f"SparseAbundanceMatrix({self.shape[0]} samples × {self.shape[1]} features, "
            f"density={self.density:.4f})"
        )

    def __repr__(self) -> str:
        """Detailed representation."""
        return str(self)
