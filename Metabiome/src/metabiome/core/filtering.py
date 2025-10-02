"""
Filtering accessors for MetabiomeDataSpace.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

import polars as pl

if TYPE_CHECKING:
    from .space import MetabiomeDataSpace


class ObsFilter:
    """Accessor for filtering samples (observations)."""

    def __init__(self, mds: MetabiomeDataSpace):
        self._mds = mds

    def __call__(self, expr: pl.Expr) -> MetabiomeDataSpace:
        """
        Filter samples (observations) based on metadata.

        Args:
            expr: A Polars expression to filter samples.

        Returns:
            A new MetabiomeDataSpace with the filtered samples.
        """
        return self._mds[expr, :]


class VarFilter:
    """Accessor for filtering features (variables)."""

    def __init__(self, mds: MetabiomeDataSpace):
        self._mds = mds

    def __call__(self, expr: pl.Expr) -> MetabiomeDataSpace:
        """
        Filter features (variables) based on annotations.

        Args:
            expr: A Polars expression to filter features.

        Returns:
            A new MetabiomeDataSpace with the filtered features.
        """
        return self._mds[:, expr]


class AbundanceFilter:
    """Accessor for filtering by abundance."""

    def __init__(self, mds: MetabiomeDataSpace):
        self._mds = mds

    def __call__(
        self,
        by: str,
        expr: pl.Expr | Callable[[pl.DataFrame], pl.DataFrame],
    ) -> MetabiomeDataSpace:
        """
        Filter samples or features based on abundance statistics.

        Parameters
        ----------
        by : str
            Either "obs" or "var".
        expr : polars.Expr or Callable[[polars.DataFrame], polars.DataFrame]
            A Polars expression or a callable for filtering.

        Returns
        -------
        MetabiomeDataSpace
            A new MetabiomeDataSpace with the filtered data.

        Examples
        --------
        >>> mds.filter.X(by="var", expr=pl.col("prevalence") > 0.1)
        >>> mds.filter.X(by="obs", expr=pl.col("sum_abundance") > 100)
        """
        ### TODO add list of Expr

        if by == "var":
            return self._filter_features(expr)
        if by == "obs":
            return self._filter_samples(expr)
        raise ValueError("`by` must be either 'obs' or 'var'")

    def _filter_features(
        self, expr: pl.Expr | Callable[[pl.DataFrame], pl.DataFrame]
    ) -> MetabiomeDataSpace:
        """Filter features by abundance."""
        feature_stats = self._mds.X.get_feature_stats()
        if isinstance(expr, pl.Expr):
            filtered_ids = (
                feature_stats.filter(expr)
                .select(self._mds.var_key)
                .to_series()
            )
        else:
            filtered_ids = (
                expr(feature_stats).select(self._mds.var_key).to_series()
            )

        return self._mds[:, pl.col(self._mds.var_key).is_in(filtered_ids)]

    def _filter_samples(
        self, expr: pl.Expr | Callable[[pl.DataFrame], pl.DataFrame]
    ) -> MetabiomeDataSpace:
        """Filter samples by abundance."""
        sample_stats = self._mds.X.get_sample_stats()
        if isinstance(expr, pl.Expr):
            filtered_ids = (
                sample_stats.filter(expr)
                .select(self._mds.obs_key)
                .to_series()
            )
        else:
            filtered_ids = (
                expr(sample_stats).select(self._mds.obs_key).to_series()
            )

        return self._mds[pl.col(self._mds.obs_key).is_in(filtered_ids), :]


class FilterAccessor:
    """Main filter accessor for MetabiomeDataSpace."""

    def __init__(self, mds: MetabiomeDataSpace):
        self._mds = mds

    def __call__(
        self,
        obs_expr: pl.Expr | None = None,
        var_expr: pl.Expr | None = None,
    ) -> MetabiomeDataSpace:
        """
        Filter on one or both axes simultaneously.

        This is a convenience method that wraps the `__getitem__` indexing.

        Args:
            obs_expr: A Polars expression to filter samples (observations).
            var_expr: A Polars expression to filter features (variables).

        Returns:
            A new MetabiomeDataSpace with the filtered data.

        Examples:
        --------
        >>> # Filter on both axes at once
        >>> mds.filter(
        ...     obs_expr=pl.col("age") > 50,
        ...     var_expr=pl.col("pathway") == "Glycolysis",
        ... )
        """
        obs_slice = obs_expr if obs_expr is not None else slice(None)
        var_slice = var_expr if var_expr is not None else slice(None)
        return self._mds[obs_slice, var_slice]

    @property
    def obs(self) -> ObsFilter:
        """Filter by sample metadata. Usage: mds.filter.obs(pl.col('age') > 50)"""
        return ObsFilter(self._mds)

    @property
    def var(self) -> VarFilter:
        """Filter by feature annotations. Usage: mds.filter.var(pl.col('pathway') == 'Glycolysis')"""
        return VarFilter(self._mds)

    @property
    def X(self) -> AbundanceFilter:
        """Filter by abundance statistics. Usage: mds.filter.X(by='var', expr=pl.col('prevalence') > 0.1)"""
        return AbundanceFilter(self._mds)
