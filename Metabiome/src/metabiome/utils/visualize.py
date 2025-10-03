from glob import glob
from pathlib import Path

import plotly.figure_factory as ff
import polars as pl


def plot_cluster_pid(datadir: str | Path) -> None:
    """
    Reads a JSON file containing PID values and generates a histogram/KDE plot.

    Parameters
    ----------
    datadir : str | Path
        Path to the directory containing the JSON file with PID values.
    """
    jsons = glob(f"{datadir}/**/*.json", recursive=True)

    df = pl.concat(
        [
            pl.read_json(json, schema={"cluster": pl.Utf8, "pid": pl.Float64})
            for json in jsons
        ]
    ).to_pandas()

    fig = ff.create_distplot(
        [df["pid"].values],
        group_labels=["Average PID"],
        show_hist=True,
        show_rug=True,
        bin_size=0.01,
    )
    fig.update_layout(
        title="Distribution of Average PID Values Across Clusters",
        xaxis_title="Average PID",
        yaxis_title="Density",
    )
    fig.show()
