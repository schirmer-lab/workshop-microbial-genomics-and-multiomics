from pathlib import Path

import polars as pl
from pyfaidx import Fasta
from tqdm import tqdm

from metabiome.annotations.cluster import ProteinCluster


def test_clusters(
    table: str | Path, fasta: str | Path, outdir: str | Path, n_jobs: int = 1
) -> list[ProteinCluster]:
    """
    Reads a TSV file mapping representative IDs to member IDs and constructs ProteinCluster objects using Polars.

    Parameters
    ----------
    table : str | Path
        Path to the input TSV file. Expected columns: mcpc_id, mcgc_id.
    fasta : str | Path
        Path to the input FASTA file.
    outdir : str | Path
        Directory where the output files will be saved.
    n_jobs : int
        Number of parallel jobs to use for processing. Default is 1.

    Returns
    -------
    list[ProteinCluster]
        A list of ProteinCluster objects, each representing a cluster of protein sequences.
    """

    df = pl.read_csv(table, separator="\t")

    if df.columns != ["mcpc_id", "mcgc_id"]:
        raise ValueError(
            f"Warning: Unexpected columns: {df.columns}. Expected ['mcpc_id', 'mcgc_id']."
        )

    df = (
        df.with_columns(
            pl.col("mcpc_id").str.split(by="::::").list.get(1).alias("mcpc_id")
        )
        .group_by("mcpc_id")
        .agg(pl.col("mcgc_id"))
    ).to_dicts()

    with Fasta(
        fasta,
        read_long_names=True,
        key_function=lambda x: x.split("::::")[1],
    ) as reader:
        for i, cluster in enumerate(
            tqdm(
                df,
                desc="Running PID calculation",
                unit="cluster",
                total=len(df),
            )
        ):
            ProteinCluster(
                reader=reader,
                outdir=outdir,
                representative_id=cluster["mcpc_id"],
                members=cluster["mcgc_id"],
                n_jobs=n_jobs,
            )()


if __name__ == "__main__":
    test_clusters(
        "data/mcgc/mcpc_mcgc_gt5.tsv",
        "data/mcgc/mcpc_mcgc_gt5.faa",
        "tmp/cluster",
        n_jobs=24,
    )

    # after running the test_clusters function, you can visualize the PID distribution
    # plot_cluster_pid("tmp/cluster")
