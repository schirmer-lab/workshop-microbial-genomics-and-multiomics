"""IndexManager / AlignedMapping utilities for ID hierarchy management.

This module provides a lightweight, explicit manager for feature ID
hierarchies commonly used in metabiome (gene_id, gc_id, mcgc_id, mcpc_id).

The IndexManager is intentionally minimal: it provides validation, lookup,
and remapping helpers that higher-level operations (concat, save/load)
can use to ensure alignment between `X`, `obs`, and `var`.
"""

from __future__ import annotations

from typing import Iterable

import polars as pl


class IndexManager:
    """Manage and validate mappings between ID namespaces.

    Example usage:
        mgr = IndexManager(id_mapping_df)
        mgr.validate()
        mapped = mgr.map_gc_to_mcgc(["gc1", "gc2"])
    """

    def __init__(self, id_mapping: pl.LazyFrame | pl.DataFrame):
        self._id_mapping = (
            id_mapping.lazy()
            if isinstance(id_mapping, pl.DataFrame)
            else id_mapping
        )

        self._df_cache: pl.DataFrame | None = None

    @property
    def df(self) -> pl.DataFrame:
        """Return the cached collected DataFrame for id_mapping."""
        if self._df_cache is None:
            self._df_cache = self._id_mapping.collect()

        return self._df_cache

    def invalidate_cache(self) -> None:
        """Clear the cached collected DataFrame. Call after id_mapping mutates."""
        self._df_cache = None

    def validate(self) -> bool:
        """Run basic validation checks on the id_mapping table.

        Ensures required columns exist and checks for duplicates.
        Returns True on success, raises ValueError otherwise.
        """
        required = {"gene_id", "gc_id", "mcgc_id", "mcpc_id"}
        cols = set(self.df.columns)

        if not required.issubset(cols):
            missing = required - cols
            raise ValueError(f"id_mapping missing required columns: {missing}")

        # Basic duplicate checks
        df = self.df

        if df.duplicated(subset=["gene_id"]).any():
            raise ValueError("Duplicate gene_id entries found in id_mapping")

        return True

    def map_gc_to_mcgc(self, gc_ids: Iterable[str]) -> list[str]:
        """Map a list of `gc_id` to `mcgc_id` using id_mapping.

        Returns list aligned with input; missing entries raise KeyError.
        """
        df = self.df.select(["gc_id", "mcgc_id"])
        mapping = {r["gc_id"]: r["mcgc_id"] for r in df.rows()}

        result: list[str] = []

        for g in gc_ids:
            if g not in mapping:
                raise KeyError(f"gc_id not found in id_mapping: {g}")
            result.append(mapping[g])

        return result

    def remap_var_names(
        self, var_names: Iterable[str], to: str = "mcgc_id"
    ) -> list[str]:
        """Remap `var_names` to the target namespace (`mcgc_id`, `gc_id`, etc.).

        `to` must be one of the columns present in id_mapping.
        """
        df = self.df

        if to not in df.columns:
            raise ValueError(f"Unknown target namespace: {to}")

        mapping = {r["gc_id"]: r[to] for r in df.rows()}
        return [mapping.get(v, v) for v in var_names]
