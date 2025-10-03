"""
Core operations for MetabiomeDataSpace including concatenation, merging, and subsetting.

Provides functions for combining multiple data spaces and performing
common operations on metagenomic data.
"""

import warnings
from typing import TYPE_CHECKING

import polars as pl
import scipy.sparse as sp

if TYPE_CHECKING:
    from .space import MetabiomeDataSpace


def concat_spaces(
    spaces: list["MetabiomeDataSpace"],
    join: str = "outer",
    batch_key: str = "cohort",
    batch_categories: list[str] | None = None,
) -> "MetabiomeDataSpace":
    """
    Concatenate multiple MetabiomeDataSpace objects.

    Essential for multi-cohort analysis and combining datasets.
    """
    from .space import MetabiomeDataSpace

    if not spaces:
        raise ValueError("No spaces provided for concatenation")

    if len(spaces) == 1:
        return spaces[0]

    if batch_categories is None:
        batch_categories = [f"batch_{i}" for i in range(len(spaces))]
    elif len(batch_categories) != len(spaces):
        raise ValueError(
            "Number of batch categories must match number of spaces"
        )

    concatenated_obs = _concat_obs(spaces, batch_key, batch_categories)
    concatenated_X = _concat_abundance(spaces, join=join)
    concatenated_var = _concat_var(spaces, join)
    concatenated_sequences = _concat_sequences(spaces)
    merged_uns = _merge_uns(spaces)

    return MetabiomeDataSpace(
        _obs=concatenated_obs,
        _X=concatenated_X,
        _var=concatenated_var,
        _sequences=concatenated_sequences,
        uns=merged_uns,
    )


def _concat_obs(
    spaces: list["MetabiomeDataSpace"],
    batch_key: str,
    batch_categories: list[str] | None,
) -> pl.LazyFrame | None:
    """Concatenate sample metadata from multiple spaces."""
    obs_dfs = []
    for i, space in enumerate(spaces):
        df = space.obs.with_columns(
            pl.lit(batch_categories[i]).alias(batch_key)
        )
        obs_dfs.append(df)

    if not obs_dfs:
        return None

    all_obs_names = []
    for df in obs_dfs:
        all_obs_names.extend(df["sample"].to_list())

    if len(all_obs_names) != len(set(all_obs_names)):
        warnings.warn(
            "Duplicate sample IDs found across spaces. Consider prefixing sample IDs."
        )

    return pl.concat([df.lazy() for df in obs_dfs], how="diagonal")


def _concat_abundance(
    spaces: list["MetabiomeDataSpace"], join: str
) -> pl.LazyFrame | None:
    """Concatenate abundance data from multiple spaces."""
    from .matrix import SparseAbundanceMatrix

    all_obs_names = [name for space in spaces for name in space.obs_names]
    all_var_names = sorted(
        list(set(name for space in spaces for name in space.X.var_names))
    )

    if join == "inner":
        var_name_sets = [set(space.X.var_names) for space in spaces]
        common_vars = list(set.intersection(*var_name_sets))
        if not common_vars:
            warnings.warn("No common features found for inner join")
            all_var_names = []
        else:
            all_var_names = sorted(common_vars)

    # Create a mapping from var_name to index
    var_to_idx = {name: i for i, name in enumerate(all_var_names)}

    # Stack matrices vertically
    matrices_to_stack = []
    for space in spaces:
        # Create a new matrix with the union of columns
        new_matrix = sp.lil_matrix(
            (space.n_obs, len(all_var_names)), dtype=space.X.data.dtype
        )

        # Create a mapping from old column index to new column index based on
        # the matrix canonical ordering available at space.X.var_names
        current_var_to_idx = {
            name: i for i, name in enumerate(space.X.var_names)
        }

        for i, var_name in enumerate(space.X.var_names):
            if var_name in var_to_idx:
                new_col_idx = var_to_idx[var_name]
                old_col_idx = current_var_to_idx[var_name]
                new_matrix[:, new_col_idx] = space.X.data[:, old_col_idx]

        matrices_to_stack.append(new_matrix.tocsr())

    concatenated_matrix = sp.vstack(matrices_to_stack, format="csr")

    return SparseAbundanceMatrix(
        data=concatenated_matrix,
        obs_names=all_obs_names,
        var_names=all_var_names,
    )


def _concat_var(
    spaces: list["MetabiomeDataSpace"], join: str
) -> pl.LazyFrame | None:
    """Concatenate feature annotations from multiple spaces."""
    var_dfs = [space.var.lazy() for space in spaces if space.var is not None]
    if not var_dfs:
        return None

    if join == "inner":
        var_name_sets = [
            set(df.select("gc_id").collect()["gc_id"].to_list())
            for df in var_dfs
        ]
        common_vars = set.intersection(*var_name_sets)
        if not common_vars:
            warnings.warn("No common features found for inner join")
            return pl.concat(var_dfs, how="diagonal").unique()

        filtered_dfs = [
            df.filter(pl.col("gc_id").is_in(list(common_vars)))
            for df in var_dfs
        ]
        return pl.concat(filtered_dfs, how="diagonal").unique()

    return pl.concat(var_dfs, how="diagonal").unique()


def _concat_sequences(spaces: list["MetabiomeDataSpace"]):
    """Concatenate sequence data from multiple spaces."""
    for space in spaces:
        if space.sequences is not None:
            return space.sequences

    return None


def _merge_uns(spaces: list["MetabiomeDataSpace"]) -> dict[str, any]:
    """Merge unstructured metadata from multiple spaces."""
    merged_uns = {}

    for i, space in enumerate(spaces):
        for key, value in space.uns.items():
            if key not in merged_uns:
                merged_uns[key] = []
            merged_uns[key].append(value)

    return merged_uns
