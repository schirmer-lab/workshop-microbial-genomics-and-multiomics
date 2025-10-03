"""
GroupedMetabiomeDataSpace: Inheritance-based grouped data operations for metagenomic analysis.

This module provides grouped data operations by inheriting from MetabiomeDataSpace,
allowing GroupedMetabiomeDataSpace to maintain all the functionality of the parent
class while handling grouped/aggregated data structures.
"""

from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING, Literal

import polars as pl

from .matrix import SparseAbundanceMatrix
from .space import MetabiomeDataSpace

if TYPE_CHECKING:
    from .space import MetabiomeDataSpace


class GroupByAccessor:
    """Accessor for grouping operations."""

    def __init__(self, mds: "MetabiomeDataSpace"):
        self._mds = mds

    def obs(self, by: str | list[str]) -> "GroupedMetabiomeDataSpace":
        """Convenience method for grouping by observation metadata."""
        return self(obs=by, var=None)

    def var(self, by: str | list[str]) -> "GroupedMetabiomeDataSpace":
        """Convenience method for grouping by feature annotations."""
        return self(obs=None, var=by)

    def __call__(
        self,
        obs: str | list[str] | pl.Expr | None = None,
        var: str | list[str] | pl.Expr | None = None,
    ) -> "GroupedMetabiomeDataSpace":
        """
        Efficient grouping method with explicit axis specification and auto-detection.

        Supports both simple auto-detection and explicit axis specification for
        complex multi-dimensional grouping scenarios.

        Parameters
        ----------
        obs : str or list[str] or pl.Expr, optional
            Sample metadata column(s) for grouping.
            (e.g., "disease_group", "age").
        var : str or list[str] or pl.Expr, optional
            Feature annotation column(s) for grouping.
            (e.g., "pfam_domain", "kegg_pathway").
        Returns
        -------
        GroupedMetabiomeDataSpace
            Lazy grouped data container ready for aggregation

        Examples
        --------
        >>> # Explicit axis specification
        >>> grouped = mds.groupby(obs="disease_group")
        >>> grouped = mds.groupby(var="pfam_domain")

        >>> # Multi-column grouping
        >>> grouped = mds.groupby(obs=["disease", "age_group"])
        >>> grouped = mds.groupby(var=["pfam", "kegg", "go_term"])

        >>> # Cross-dimensional grouping
        >>> grouped = mds.groupby(obs=["disease"], var=["pfam"])
        """
        obs_cols = []
        if isinstance(obs, str):
            obs_cols = [obs]
        elif isinstance(obs, list):
            obs_cols = obs

        var_cols = []
        if isinstance(var, str):
            var_cols = [var]
        elif isinstance(var, list):
            var_cols = var

        if isinstance(obs, pl.Expr):
            raise NotImplementedError(
                "Expression-based grouping is not yet implemented."
            )

        if obs_cols:
            missing_obs = set(obs_cols) - set(
                self._mds._obs.collect_schema().names()
            )
            if missing_obs:
                raise ValueError(
                    f"Sample grouping columns not found: {missing_obs}"
                )

        if var_cols:
            missing_features = set(var_cols) - set(
                self._mds._var.collect_schema().names()
            )
            if missing_features:
                raise ValueError(
                    f"Feature grouping columns not found: {missing_features}"
                )

        abundance_lf = self._mds._X.to_long()
        grouped_X = abundance_lf
        grouped_obs = self._mds._obs
        grouped_var = self._mds._var

        if obs_cols and var_cols:
            # Cross-dimensional grouping
            abundance_lf = abundance_lf.join(
                self._mds._obs, on=self._mds.obs_key, how="inner"
            ).join(self._mds._var, on=self._mds.var_key, how="inner")
            grouped_X = abundance_lf.group_by(obs_cols + var_cols).agg(
                pl.col("abundance")
            )
            grouped_obs = self._mds._obs.group_by(obs_cols).agg(pl.all())
            grouped_var = self._mds._var.group_by(var_cols).agg(pl.all())

        elif obs_cols:
            # Sample-only grouping
            abundance_lf = abundance_lf.join(
                self._mds._obs, on=self._mds.obs_key, how="inner"
            )
            grouped_X = abundance_lf.group_by(
                obs_cols + [self._mds.var_key]
            ).agg(pl.col("abundance"))
            grouped_obs = self._mds._obs.group_by(obs_cols).agg(pl.all())

        elif var_cols:
            # Feature-only grouping
            abundance_lf = abundance_lf.join(
                self._mds._var, on=self._mds.var_key, how="inner"
            )
            grouped_X = abundance_lf.group_by(
                var_cols + [self._mds.obs_key]
            ).agg(pl.col("abundance"))
            grouped_var = self._mds._var.group_by(var_cols).agg(pl.all())

        return GroupedMetabiomeDataSpace(
            X=grouped_X,
            obs=grouped_obs,
            var=grouped_var,
            obs_columns=obs_cols,
            var_columns=var_cols,
            obs_key=self._mds.obs_key,
            var_key=self._mds.var_key,
            aggregated=False,
            sequences=self._mds._sequences,
            id_mapping=self._mds._id_mapping,
            uns=self._mds.uns,
        )


class GroupedMetabiomeDataSpace(MetabiomeDataSpace):
    """
    Grouped data container that is self-contained and independent of its parent.

    This class extends MetabiomeDataSpace to handle both grouped data (with list columns)
    and aggregated data (flat structure), providing full API compatibility with the parent class.

    Examples
    --------
    >>> # Disease group analysis
    >>> grouped = mds.groupby.obs("disease_group")
    >>> disease_profiles = grouped.agg("mean")

    >>> # Pfam domain grouping
    >>> pfam_grouped = mds.groupby.var("pfam_domain")
    >>> pfam_profiles = pfam_grouped.agg("sum")
    """

    def __init__(
        self,
        X: pl.LazyFrame,
        obs: pl.LazyFrame,
        var: pl.LazyFrame,
        obs_columns: list[str],
        var_columns: list[str],
        obs_key: str,
        var_key: str,
        aggregated: bool = False,
        sequences=None,
        id_mapping=None,
        uns: dict | None = None,
    ):
        """
        Initialize a self-contained grouped data space.
        """
        self._X = X
        self._obs = obs
        self._var = var
        self._obs_columns = obs_columns
        self._var_columns = var_columns
        self._aggregated = aggregated

        self.obs_key = obs_key
        self.var_key = var_key
        self._sequences = sequences
        self._id_mapping = id_mapping
        self.uns = uns.copy() if uns is not None else {}
        self._backing_store = None

    def agg(
        self,
        func: Literal[
            "first",
            "last",
            "min",
            "max",
            "mean",
            "median",
            "std",
            "sum",
            "var",
            "count",
        ],
    ) -> "MetabiomeDataSpace":
        """
        Perform aggregation on grouped data.

        Returns
        -------
        MetabiomeDataSpace
            A new MetabiomeDataSpace instance with aggregated data, enabling further chaining.
        """
        if self._aggregated:
            raise ValueError(
                "Cannot aggregate data that has already been aggregated."
            )

        if not isinstance(func, str):
            raise NotImplementedError(
                "Multiple or dictionary-based aggregations are not yet implemented."
            )

        expr = getattr(pl.col("abundance").list, func)()
        aggregated_X = self._X.with_columns(expr.alias("abundance"))

        new_obs = self._obs
        new_var = self._var
        obs_col = self.obs_key
        var_col = self.var_key
        new_sequences = self._sequences
        new_id_mapping = self._id_mapping

        if self._obs_columns:
            obs_col = "obs"
            new_obs = (
                self._obs.group_by(self._obs_columns)
                .agg(pl.all().exclude(self._obs_columns).first())
                .with_columns(
                    pl.concat_str(
                        [pl.col(c).cast(pl.Utf8) for c in self._obs_columns],
                        separator=":::",
                        ignore_nulls=True,
                    ).alias(obs_col)
                )
            )
            aggregated_X = aggregated_X.with_columns(
                pl.concat_str(
                    [pl.col(c).cast(pl.Utf8) for c in self._obs_columns],
                    separator=":::",
                    ignore_nulls=True,
                ).alias(obs_col)
            )

        if self._var_columns:
            var_col = "var"
            # Collect schema to check dtypes
            schema = self._var.collect_schema()
            # Build aggregation expressions: for List columns, take .list.first() to flatten; otherwise, .first()
            agg_exprs = [
                (
                    pl.col(col).list.first()
                    if schema[col] == pl.List
                    else pl.col(col).first()
                ).cast(pl.Utf8)
                for col in schema.names()
                if col not in self._var_columns
            ]
            # Collect to DataFrame to ensure correct schema inference
            grouped_var_df = self._var.collect()
            new_var_df = (
                grouped_var_df.group_by(self._var_columns)
                .agg(agg_exprs)
                .with_columns(
                    pl.concat_str(
                        [pl.col(c).cast(pl.Utf8) for c in self._var_columns],
                        separator=":::",
                        ignore_nulls=True,
                    ).alias(var_col)
                )
            )
            # Cast List columns to strings
            for col in new_var_df.columns:
                if new_var_df[col].dtype == pl.List:
                    new_var_df = new_var_df.with_columns(
                        pl.col(col).list.first().cast(pl.Utf8).alias(col)
                    )
            new_var = new_var_df.lazy()
            aggregated_X = aggregated_X.with_columns(
                pl.concat_str(
                    [pl.col(c).cast(pl.Utf8) for c in self._var_columns],
                    separator=":::",
                    ignore_nulls=True,
                ).alias(var_col)
            )

            # TODO: handle sequences and id_mapping after mds grouped and aggregated
            new_sequences = None
            new_id_mapping = None

        return MetabiomeDataSpace.from_filtered_data(
            obs=new_obs,
            X=SparseAbundanceMatrix.from_polars(
                aggregated_X,
                obs_col=obs_col,
                var_col=var_col,
            ),
            var=new_var,
            sequences=new_sequences,
            id_mapping=new_id_mapping,
            uns=self.uns,
            obs_key=obs_col,
            var_key=var_col,
        )

    def __repr__(self) -> str:
        """Developer-friendly representation."""
        obs_info = f"obs={self._obs_columns}" if self._obs_columns else ""
        var_info = f"var={self._var_columns}" if self._var_columns else ""

        info_parts = [part for part in [obs_info, var_info] if part]
        info_str = ", ".join(info_parts) if info_parts else "no grouping"

        state = "aggregated" if self._aggregated else "grouped"

        return f"GroupedMetabiomeDataSpace({info_str}, state={state})"

    @cached_property
    def obs(self) -> pl.DataFrame:
        """Get metadata as DataFrame."""
        return self._obs.collect()

    @cached_property
    def var(self) -> pl.DataFrame:
        """Get annotation as DataFrame."""
        return self._var.collect()

    @property
    def X(self) -> "SparseAbundanceMatrix":
        """
        Access the abundance matrix.

        Raises
        ------
        AttributeError
            On a `GroupedMetabiomeDataSpace` because this object represents a pending
            aggregation. Call `.agg(func)` to create a new `MetabiomeDataSpace`
            with an aggregated `.X` matrix.
        """
        raise AttributeError(
            "Cannot access .X on a GroupedMetabiomeDataSpace. This object represents "
            "a pending aggregation. Call .agg(func) to create a new MetabiomeDataSpace "
            "with an aggregated .X matrix. To inspect the intermediate grouped data, "
            "use the .preview() method."
        )

    def preview(self) -> pl.DataFrame:
        """
        Preview the intermediate grouped abundance data before aggregation.

        This method is for inspection purposes. It returns a DataFrame where the
        'abundance' column contains lists of values for each group.

        Returns
        -------
        polars.DataFrame
            The collected intermediate LazyFrame.
        """
        return self._X.collect()
