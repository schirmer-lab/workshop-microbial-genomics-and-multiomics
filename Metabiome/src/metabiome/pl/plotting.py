"""
Plotting accessors for MetabiomeDataSpace.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import plotly.express as px
import plotly.graph_objects as go
import polars as pl

if TYPE_CHECKING:
    from metabiome.core import MetabiomeDataSpace


class PlottingAccessor:
    """
    Accessor for plotting functions, available as `mds.pl`.

    This class provides a namespace for plotting methods that operate on a
    MetabiomeDataSpace object.
    """

    def __init__(self, mds: MetabiomeDataSpace):
        self._mds = mds

    def sankey(
        self,
        hierarchy_cols: list[str],
        min_abundance: float = 1e-2,
        height: int = 800,
        font_size: int = 8,
        title: str = "Abundance Flow Diagram",
    ):
        """
        Generate a Sankey diagram of hierarchical feature annotations.

        Parameters
        ----------
        hierarchy_cols : list[str]
            A list of columns in `mds.var` that define the hierarchical flow,
            e.g., `['domain', 'phylum', 'species']` or `['category', 'function']`.
        min_abundance : float, optional
            The minimum total abundance for a path to be included in the diagram,
            by default 1e-2.
        height : int, optional
            The height of the figure in pixels, by default 800.
        font_size : int, optional
            The font size for the diagram, by default 8.
        title : str, optional
            The title of the figure, by default "Abundance Flow Diagram".
        """
        if not hierarchy_cols or len(hierarchy_cols) < 2:
            raise ValueError(
                "`hierarchy_cols` must contain at least two columns."
            )

        mds = self._mds
        abundance_lf = mds.X.to_long()

        # Ensure join key datatypes match
        var_dtype = mds._var.collect_schema()[mds.var_key]
        abundance_lf = abundance_lf.with_columns(
            pl.col(mds.var_key).cast(var_dtype)
        )

        # Filter hierarchy_cols to only those available in var
        available_cols = set(mds._var.collect_schema().names())
        hierarchy_cols = [c for c in hierarchy_cols if c in available_cols]

        if len(hierarchy_cols) < 2:
            raise ValueError(
                f"Not enough hierarchy columns found in mds.var. "
                f"Available columns: {sorted(available_cols)}. "
                "For aggregated data, use appropriate hierarchy columns."
            )

        annotation_lf = mds._var.select(hierarchy_cols + [mds.var_key])

        # Collect the var DataFrame first to avoid schema issues
        var_df = mds._var.collect(type_coercion=True, _type_check=False)
        annotation_df = var_df.select(hierarchy_cols + [mds.var_key])
        annotation_lf = annotation_df.lazy()

        # Flatten List columns to strings
        for col in hierarchy_cols:
            dtype = annotation_df[col].dtype
            if dtype == pl.List:
                annotation_lf = annotation_lf.with_columns(
                    pl.col(col).list.first().alias(col)
                )
                temp_df = annotation_lf.collect()
                if temp_df[col].dtype == pl.List:
                    annotation_lf = annotation_lf.with_columns(
                        pl.col(col).list.first().alias(col)
                    )
                    temp_df = annotation_lf.collect()
                    if temp_df[col].dtype == pl.List:
                        annotation_lf = annotation_lf.with_columns(
                            pl.col(col).list.join(", ").alias(col)
                        )

        annotation_df = annotation_lf.collect()
        annotation_lf = annotation_df.lazy()

        filtered_annotation_lf = annotation_lf.filter(
            pl.all_horizontal(
                (pl.col(c).is_not_null())
                & (pl.col(c) != "")
                & (pl.col(c) != "NA")
                for c in hierarchy_cols
            )
        )

        df = (
            abundance_lf.join(filtered_annotation_lf, on=mds.var_key)
            .group_by(hierarchy_cols)
            .agg(pl.mean("abundance"))
            .filter(pl.col("abundance") > min_abundance)
            .collect()
        )

        # Preprocess: Convert list columns to strings by taking the first element
        for col in hierarchy_cols:
            if df[col].dtype == pl.List:
                df = df.with_columns(pl.col(col).list.first().alias(col))

        all_nodes = set()
        links_map = {}
        for row in df.iter_rows(named=True):
            for i in range(len(hierarchy_cols) - 1):
                source = row[hierarchy_cols[i]]
                target = row[hierarchy_cols[i + 1]]
                if source and target and source != target:
                    all_nodes.add(source)
                    all_nodes.add(target)
                    link_key = (source, target)
                    links_map[link_key] = (
                        links_map.get(link_key, 0) + row["abundance"]
                    )

        if not links_map:
            raise ValueError(
                "No links could be generated for the Sankey diagram. "
                "Check for missing annotations or low abundance values."
            )

        links = [
            {"source": s, "target": t, "value": v}
            for (s, t), v in links_map.items()
        ]
        nodes = list(all_nodes)
        node_indices = {name: i for i, name in enumerate(nodes)}

        fig = go.Figure(
            data=[
                go.Sankey(
                    node=dict(
                        pad=25,
                        thickness=15,
                        line=dict(color="black", width=0.5),
                        label=nodes,
                    ),
                    link=dict(
                        source=[node_indices[link["source"]] for link in links],
                        target=[node_indices[link["target"]] for link in links],
                        value=[link["value"] for link in links],
                        hovertemplate="Flow from %{source.label} to %{target.label}: %{value:.2e}<extra></extra>",
                    ),
                )
            ]
        )
        fig.update_layout(title_text=title, font_size=font_size, height=height)
        fig.show()

    def boxplot(
        self,
        feature_name: str,
        x_axis_col: str,
        feature_type_col: str | None = None,
        title: str | None = None,
        point_size: int = 3,
        color_map: dict[str, str] | None = {
            "Healthy": "#2166ac",
            "nonIBD": "#2166ac",
            "CD": "#b2182b",
            "UC": "#d6604d",
            "CRC": "#762a83",
            "MP": "#9970ab",
            "adenoma": "#c2a5cf",
        },
    ):
        """
        Generate a boxplot for a single feature, categorized by a sample metadata column.

        Parameters
        ----------
        feature_name : str
            The name of the feature (e.g., a species or gene) to plot.
            This name must exist in the column specified by `feature_type_col`.
        x_axis_col : str
            The column from `mds.obs` to use for the x-axis categories
            (e.g., 'disease_group').
        feature_type_col : str, optional
            The column from `mds.var` that contains the `feature_name`.
            If None, it is assumed that the `mds` is already aggregated
            and `feature_name` is the `mds.var_key`. Defaults to None.
        title : str, optional
            The title of the plot. If None, a default title is generated.
        point_size : int, optional
            The size of the overlaid points. Defaults to 3.
        color_map : dict[str, str], optional
            A dictionary mapping category names to colors. Only categories present in this
            dictionary will be included in the plot, ordered according to the key sequence.
            If None, uses a default color scheme with predefined colors for common disease groups.
            Defaults to a predefined color map for disease groups.
        """
        mds = self._mds

        if feature_type_col and mds.var_key != feature_type_col:
            mds = mds.groupby.var(feature_type_col).agg("sum")

        feature_mds = mds.filter.var(pl.col(mds.var_key) == feature_name)

        if feature_mds.n_vars == 0:
            raise ValueError(
                f"Feature '{feature_name}' not found in mds.var column '{mds.var_key}'."
            )

        abundance_df = feature_mds.X.to_long().collect()
        meta_df = feature_mds.obs.select([feature_mds.obs_key, x_axis_col])

        plot_df = abundance_df.join(meta_df, on=feature_mds.obs_key)

        plot_df = plot_df.with_columns(
            pl.col("abundance").sqrt().alias("sqrt_abundance")
        )

        # Reorder DataFrame according to color_map keys if provided
        if color_map:
            color_keys = list(color_map.keys())

            plot_df = plot_df.filter(pl.col(x_axis_col).is_in(color_keys))
            order_mapping = {cat: i for i, cat in enumerate(color_keys)}

            plot_df = (
                plot_df.with_columns(
                    pl.col(x_axis_col)
                    .map_elements(
                        lambda x: order_mapping.get(x, len(color_keys)),
                        return_dtype=pl.Int64,
                    )
                    .alias("_order")
                )
                .sort("_order")
                .drop("_order")
            )

        plot_title = (
            title or f"Sqrt Abundance of {feature_name} by {x_axis_col}"
        )

        fig = px.box(
            plot_df,
            x=x_axis_col,
            y="sqrt_abundance",
            points="outliers",
            title=plot_title,
            color=x_axis_col,
            color_discrete_map=color_map,
        )
        fig.update_traces(marker_size=point_size, selector=dict(type="box"))
        fig.show()

    def lollipop(
        self,
        title: str = "Mutation Lollipop Plot",
        width: int = 1200,
        height: int = 600,
        threads: int | None = None,
        min_count: int = 1,
        top_n: int | None = None,
        smoothing_window: int | None = 50,
    ):
        """
        Generate a lollipop plot of sequence mutations against a consensus sequence.

        This plot is useful for visualizing mutation hotspots and the types of
        mutations occurring within a group of aligned gene sequences.

        Parameters
        ----------
        title : str, optional
            The title of the plot, by default "Mutation Lollipop Plot".
        height : int, optional
            The height of the figure in pixels, by default 600.
        threads : int, optional
            Number of threads to use for the mutation annotation pipeline.
            Defaults to all available cores.
        min_count : int, optional
            Minimum count of mutations to include in the plot. Defaults to 1.
        top_n : int, optional
            If specified, show only the top N mutations by count. Defaults to None.
        smoothing_window : int, optional
            The size of the sliding window for smoothing the positional PID line.
            If None, no smoothing is applied. Defaults to 50.
        """
        mds = self._mds

        if mds.n_vars > 1000:
            logging.warning(
                "Warning: Generating a lollipop plot for a large number of "
                "sequences (>1000) may be slow and result in a cluttered plot."
            )

        # Run the gene analysis pipeline to get mutations
        gene_group = mds.genes
        if gene_group.mutations is None:
            logging.info("Running mutation annotation pipeline...")
            gene_group(threads=threads)

        mutations_df = gene_group.mutations
        positional_pid = gene_group._positional_pid

        if mutations_df is None or mutations_df.is_empty():
            logging.warning("No mutations found to plot.")
            return

        if positional_pid is None:
            logging.warning("Positional PID data not found.")
            return

        # Use pre-aggregated data from catalog.py
        plot_data = mutations_df.filter(pl.col("count") >= min_count)

        if top_n is not None:
            plot_data = (
                plot_data.sort("count", descending=True)
                .head(top_n)
                .sort("position")
            )

        gene_length = len(positional_pid)

        color_map = {
            "missense": "blue",
            "nonsense": "red",
            "synonymous": "green",
            "insertion": "purple",
            "deletion": "orange",
            "stop loss": "brown",
            "silent": "grey",
            "unknown": "black",
        }

        # Get group PID for horizontal line
        group_pid = (
            mutations_df["group_pid"].unique()[0]
            if "group_pid" in mutations_df.columns
            else None
        )
        plot_title = (
            f"{title} (Average PID: {group_pid * 100:.2f}%)"
            if group_pid is not None
            else title
        )

        fig = go.Figure()

        # Add the raw positional PID line
        fig.add_trace(
            go.Scatter(
                x=list(range(gene_length)),
                y=positional_pid,
                mode="lines",
                name="Raw Conservation",
                line=dict(color="lightgrey", width=1),
                hoverinfo="skip",
            )
        )

        # Add the smoothed positional PID line
        if smoothing_window:
            smoothed_pid = (
                pl.Series(positional_pid)
                .rolling_mean(window_size=smoothing_window, center=True)
                .to_list()
            )
            fig.add_trace(
                go.Scatter(
                    x=list(range(gene_length)),
                    y=smoothed_pid,
                    mode="lines",
                    name="Smoothed Conservation",
                    line=dict(color="black", width=2),
                    hoverinfo="skip",
                )
            )

        for mutation_type_tuple, group in plot_data.group_by("mutation"):
            mutation_type = mutation_type_tuple[0]
            positions_bp = group["position_bp"].to_list()

            # Get the PID at each mutation position for the lollipop height
            y_values = [positional_pid[p] for p in positions_bp]

            hover_text = [
                f"Position (AA): {r['position']}<br>"
                f"Position (bp): {r['position_bp']}<br>"
                f"Mutation: {r['mutation']}<br>"
                f"Change: {r['ref_aa']} -> {r['var_aa']}<br>"
                f"Count: {r['count']}<br>"
                f"Frequency: {r['percentage']:.2f}%"
                for r in group.iter_rows(named=True)
            ]

            # Add stems
            for i, p_bp in enumerate(positions_bp):
                fig.add_shape(
                    type="line",
                    x0=p_bp,
                    y0=0,
                    x1=p_bp,
                    y1=y_values[i],
                    line=dict(
                        color=color_map.get(mutation_type, "grey"), width=2
                    ),
                )

            # Add markers
            fig.add_trace(
                go.Scatter(
                    x=positions_bp,
                    y=y_values,
                    mode="markers",
                    name=mutation_type,
                    marker=dict(
                        color=color_map.get(mutation_type, "grey"), size=10
                    ),
                    hoverinfo="text",
                    text=hover_text,
                )
            )

        fig.update_layout(
            title=plot_title,
            xaxis_title="Location within the gene (bp)",
            yaxis_title="Percent Identity (PID)",
            height=height,
            xaxis=dict(range=[0, gene_length]),
            yaxis=dict(range=[0, 101]),
            showlegend=True,
        )

        fig.show()
