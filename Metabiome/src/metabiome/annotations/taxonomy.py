import io
import logging
import re
import subprocess
import tarfile
from abc import ABC, abstractmethod
from collections import namedtuple
from functools import cache
from hashlib import md5
from pathlib import Path

import polars as pl
import requests
from joblib import Parallel, delayed
from pymongo import MongoClient
from tqdm import tqdm

from ..utils._helpers import timer

NAME_CLASSES = [
    "synonym",
    "equivalent name",
    "genbank equivalent name",
    "anamorph",
    "genbank synonym",
    "genbank anamorph",
    "teleomorph",
    "scientific name",
]

ALLOWED_RANKS = [
    "domain",
    "kingdom",
    "phylum",
    "class",
    "order",
    "family",
    "genus",
    "species",
]

GTDB_RANKS = [
    "domain",
    "phylum",
    "class",
    "order",
    "family",
    "genus",
    "species",
]

METAPHLAN_RANKS = [
    "kingdom",
    "phylum",
    "class",
    "order",
    "family",
    "genus",
    "species",
]


class Taxonomy(ABC):
    def __init__(self, update: bool = False):
        self.update = update

    @abstractmethod
    def __enter__(self):
        pass

    @abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class NCBI(Taxonomy):
    def __init__(self, update: bool = False):
        super().__init__(update)
        self.url = "https://ftp.ncbi.nih.gov/pub/taxonomy/taxdump.tar.gz"
        if self._verify_taxdump():
            logging.info("👍 NCBI taxonomy is up-to-date.")
        else:
            logging.info("🔄 Updating NCBI taxonomy.")
            self._update_taxonomy_from_ncbi()

    def __enter__(self):
        self.client = MongoClient("mongodb://localhost:27017/", maxPoolSize=50)
        self.client.server_info()
        self.db = self.client["NCBI"]
        logging.info("✅ Connected to MongoDB successfully.")
        return self.db

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.client.close()
        logging.info("🔌 MongoDB connection closed successfully")

    def _create_indexes(self, db):
        logging.info("Creating indexes...")
        db.names.create_index(
            [("tax_name", "text")], name="name", background=True
        )
        logging.info("Indexes created successfully.")

    def _verify_taxdump(self, taxdump: str = "tmp/taxdump.tar.gz") -> bool:
        taxdump = Path(taxdump)
        try:
            response = requests.get(f"{self.url}.md5")
            response.raise_for_status()
            expected = response.text.split()[0]
            with taxdump.open("rb") as f:
                actual = md5(f.read()).hexdigest()
        except Exception:
            return False

        if expected == actual:
            logging.info(f"{taxdump.name} is up-to-date.")
            return True
        logging.error(f"{taxdump.name} is outdated.")
        return False

    def _download_taxdump(self) -> Path:
        Path("tmp").mkdir(parents=True, exist_ok=True)
        taxdump = Path("tmp") / "taxdump.tar.gz"

        try:
            subprocess.run(["wget", "-O", taxdump, self.url], check=True)
            logging.info(f"Downloaded taxdump to {taxdump}.")

            return taxdump

        except subprocess.CalledProcessError as e:
            logging.error(f"wget error: {e}")
            raise RuntimeError(
                f"Unable to download taxdump from {self.url}"
            ) from e

    def _update_taxonomy_from_ncbi(self):
        taxdump_path = self._download_taxdump()
        try:
            counts = self._load_taxdump_into_mongodb(taxdump_path)
            logging.info(f"Loaded {counts} records into MongoDB.")
        except Exception as e:
            logging.error(f"Error occurred while updating taxonomy: {e}")

    @timer()
    def _load_taxdump_into_mongodb(self, taxdump_path: str):
        with tarfile.open(taxdump_path, "r:gz") as tar:
            names = (
                pl.read_csv(
                    io.TextIOWrapper(tar.extractfile("names.dmp")),
                    separator="|",
                    has_header=False,
                    columns=[0, 1, 3],
                    new_columns=["tax_id", "tax_name", "name_class"],
                    truncate_ragged_lines=True,
                    skip_rows=1,
                )
                .filter(pl.col("name_class").str.contains("scientific name"))
                .select(["tax_id", "tax_name"])
                .with_columns(
                    [
                        pl.col("tax_id").str.strip_chars().cast(pl.Int32),
                        pl.col("tax_name").str.strip_chars(),
                    ]
                )
            )

        records = names.rows(named=True)

        with self as db:
            db.names.insert_many(records, ordered=False)
            self._create_indexes(db)

        return len(records)

    def explain_match_names(self, names: list[str]) -> dict:
        with self as db:
            return db.names.find({"name": {"$in": names}}).explain()


def parse_ncbi_taxonomy(taxdump: str | Path) -> pl.DataFrame:
    """The function `parse_ncbi_taxonomy` reads and processes NCBI taxonomy data files to extract taxonomic
    information.

    Parameters
    ----------
    taxdump : str | Path
        The `taxdump` parameter in the `parse_ncbi_taxonomy` function is expected to be a string or PathLike
    representing the path to a compressed tar file containing taxonomic data files. The function reads
    and processes the data files within the tar archive to extract taxonomic information such as tax
    IDs, taxonomic names

    Returns
    -------
        The function `parse_ncbi_taxonomy` returns a concatenated DataFrame containing taxonomic
    information parsed from the NCBI taxdump files, including taxonomic IDs, taxonomic names, name
    classes, parent IDs, and ranks.

    """

    with tarfile.open(taxdump, "r:gz") as tar:
        names = (
            pl.scan_csv(
                io.TextIOWrapper(tar.extractfile("names.dmp")),
                separator="|",
                has_header=False,
                new_columns=["tax_id", "tax_name", "", "name_class"],
                truncate_ragged_lines=True,
                skip_rows=2,
            )
            .with_columns(
                [
                    pl.col("tax_id").str.strip_chars(),
                    pl.col("tax_name").str.strip_chars(),
                    pl.col("name_class").str.strip_chars(),
                ]
            )
            .filter(
                ~pl.col("tax_name").str.contains("cellular organisms")
                & pl.col("name_class").is_in(NAME_CLASSES)
            )
            .select(["tax_id", "tax_name", "name_class"])
        )

        nodes = (
            pl.scan_csv(
                io.TextIOWrapper(tar.extractfile("nodes.dmp")),
                separator="|",
                has_header=False,
                new_columns=[
                    "tax_id",
                    "parent_id",
                    "rank",
                    *[""] * 10,
                ],
                truncate_ragged_lines=True,
                skip_rows=1,
            )
            .select(["tax_id", "parent_id", "rank"])
            .with_columns(
                [
                    pl.col("tax_id").str.strip_chars(),
                    pl.col("parent_id").str.strip_chars(),
                    pl.col("rank").str.strip_chars(),
                ]
            )
        )

        taxa = nodes.join(names, on="tax_id", how="inner")

        merged = (
            pl.scan_csv(
                io.TextIOWrapper(tar.extractfile("merged.dmp")),
                separator="|",
                has_header=False,
                new_columns=["old_tax_id", "new_tax_id"],
                truncate_ragged_lines=True,
            )
            .select(["old_tax_id", "new_tax_id"])
            .with_columns(
                pl.col("old_tax_id").str.strip_chars(),
                pl.col("new_tax_id").str.strip_chars(),
            )
            .join(
                taxa,
                left_on="new_tax_id",
                right_on="tax_id",
                how="inner",
            )
            .drop(["new_tax_id"])
        ).rename({"old_tax_id": "tax_id"})

    return pl.concat([taxa, merged]).collect()


def build_lineage(taxa: pl.DataFrame, out: str | Path = "tmp/taxa.csv"):
    """The function `build_lineage` constructs lineages for taxa based on their parent-child relationships
    and ranks, storing the results in a CSV file.

    Parameters
    ----------
    taxa : pl.DataFrame
        The `taxa` parameter in the `build_lineage` function is expected to be a DataFrame containing
    taxonomic information. The function processes this DataFrame to build lineages for each taxonomic
    entry based on the parent-child relationships defined in the DataFrame. The function uses the
    taxonomic IDs, parent IDs

    out : str | Path
    PathLike str to the output directory for a constructed NCBI database in tabular format.

    """
    Node = namedtuple("Node", ["tax_id", "parent_id", "rank", "name"])

    taxonomy = taxa.filter(pl.col("name_class") == "scientific name").to_dict(
        as_series=False
    )

    taxonomy = dict(
        zip(
            taxonomy["tax_id"],
            zip(
                taxonomy["tax_id"],
                taxonomy["parent_id"],
                taxonomy["rank"],
                taxonomy["tax_name"],
            ),
        )
    )

    @cache
    def get_lineage(tax_id: str) -> str:
        node = taxonomy.get(tax_id)

        if not node:
            return ""

        node = Node(*node)

        parent_lineage = get_lineage(node.parent_id)
        if node.rank in ALLOWED_RANKS:
            lineage = (
                f"{parent_lineage}|{node.name}"
                if parent_lineage
                else f"{node.name}"
            )
        else:
            lineage = parent_lineage

        return lineage

    with tqdm(total=len(taxa), desc="Building lineages") as pbar:
        lineages = []
        for tid in taxa["tax_id"]:
            lineages.append(get_lineage(tid))
            pbar.update(1)

    taxa = taxa.with_columns(pl.Series("lineage", lineages))
    taxa.write_csv(Path(out))


def process_metaphlan_annotations(
    metaphlan: str | Path,
    ncbi: str | Path,
    out: str | Path,
) -> pl.DataFrame:
    """This Python function processes Metaphlan annotations and lineage data to create a DataFrame and
    write the results to a CSV file, mapped MetaPhlAn taxonomy file will be named metaphlan.csv.

    Parameters
    ----------
    metaphlan : str | Path
        PathLike str to the unmapped MetaPhlAn annotations in .json format.
    data file containing Metaphlan annotations.
    ncbi : str | Path
        Pathlike str to the preprocessed `NCBI lineage` file.
    out : str | Path
        Pathlike str to the output directory.

    Returns
    -------
        The NCBI taxa of all MetaPhlAn Markers from its database in DataFrame format.

    """
    df = (
        pl.scan_csv(
            metaphlan,
            separator="\t",
            has_header=False,
            new_columns=["prefix", "data"],
        )
        .with_columns(
            [
                pl.col("prefix").str.extract_groups(r"(\d+)__(.+)"),
                pl.col("data")
                .str.extract(r"'taxon':\s*'([^']+)'")
                .alias("taxonomy"),
            ]
        )
        .with_columns(
            pl.col("prefix").struct["1"].alias("tax_id"),
            pl.col("prefix").struct["2"].alias("marker"),
        )
        .drop(["prefix", "data"])
        .with_columns(
            [
                pl.col("taxonomy")
                .str.split("|")
                .list.eval(pl.element().str.extract(r"[kpcofgs]__(.*)"))
                .list.to_struct(
                    n_field_strategy="max_width",
                    fields=METAPHLAN_RANKS,
                )
                .alias("nested"),
            ]
        )
        .select(
            [
                "tax_id",
                "marker",
                "nested",
            ]
        )
        .unnest("nested")
    )

    lineage = pl.scan_csv(
        ncbi, has_header=True, infer_schema=False, null_values=[""]
    )

    df = df.join(
        lineage.select("tax_id", "lineage").unique(), on="tax_id", how="left"
    ).filter(
        pl.col("lineage").is_not_null()
    )  # TODO missing one tax_id = 2058935, node is deleted

    df.collect().write_csv(Path(out) / "metaphlan.csv")
    return df


def process_gtdb_annotations(
    gtdb: str | Path, ncbi: str | Path, out: str | Path
) -> pl.DataFrame:
    """The function `process_gtdb_annotations` processes GTDB annotations by extracting taxonomy
    information and joining with lineage data before writing the result to a CSV file named gtdb.csv under `out` directory.
    This function will automatically parse all .tsv files in the `gtdb` directory.

    Parameters
    ----------
    gtdb : str | Path
        PathLike str to the directory containing all GTDB annotations in .tsv format.
    ncbi : str | Path
        PathLike str to the preprocessed `NCBI lineage` file.
    out : str | Path
        Pathlike str to the output directory.

    Returns
    -------
        All GTDB taxa left joined with the NCBI taxa in DataFrame format.

    """
    df = (
        pl.scan_csv(
            Path(f"{gtdb}/*.tsv"),
            separator="\t",
            has_header=True,
            infer_schema=False,
        )
        .with_columns(
            [
                pl.col("gtdb_taxonomy")
                .str.split(";")
                .list.eval(pl.element().str.extract(r"[dpcofgs]__(.*)"))
                .list.to_struct(
                    n_field_strategy="max_width",
                    fields=GTDB_RANKS,
                )
                .alias("nested"),
                pl.col("ncbi_taxid").alias("tax_id"),
            ]
        )
        .select(["tax_id", "accession", "nested"])
        .unnest("nested")
    )

    lineage = pl.scan_csv(
        ncbi, has_header=True, infer_schema=False, null_values=[""]
    )

    df = df.join(
        lineage.select("tax_id", "lineage").unique(), on="tax_id", how="left"
    ).filter(pl.col("lineage").is_not_null())

    df.collect().write_csv(Path(out) / "gtdb.csv")

    return df


def merge_taxa(
    query: pl.LazyFrame,
    gtdb: str | Path,
    metaphlan: str | Path,
    ncbi: str | Path,
    out: str | Path,
) -> pl.DataFrame:
    """The function `merge_taxa` merges taxonomic information from two datasets based on specified ranks
    and outputs the result to a CSV file.

    Parameters
    ----------
    query : pl.LazyFrame
        The taxonomic annotations to want to merge, should contain the following columns:
        - msp_id: MSP ID
        - gtdb_taxonomy: GTDB taxonomy
        - metaphlan_clade: MetaPhlAn clade
        - score: MetaPhlAn score

    gtdb : str | Path
        PathLike str or Path to the mapped `GTDB` NCBI taxonomy in .csv format.

    metaphlan : str | Path
        PathLike str or Path to the mapped `MetaPhlAn` NCBI taxanomy in .csv format.

    ncbi : str | Path
        PathLike str or Path to the preprocessed `NCBI lineage` file.

    out : str | Path
        Output csv file PathLike str or Path.

    Returns
    -------
        The function `merge_taxa` returns a DataFrame containing merged taxonomic information of GTDB and MetaPhlAn
    for the given input data. The merged DataFrame is then written to a CSV file named
    "merged.taxa.csv" in the "output" directory.

    """

    def reduce_lineage(lineages: dict) -> dict:
        """reduce all lineages in a single row"""

        def merge(lineage: list[str]):
            if not lineage:
                return None

            to_merge = [s.split("|") for s in lineage if s is not None]

            merged = list(
                set.intersection(
                    *map(
                        set,
                        to_merge,
                    )
                )
            )

            return "|".join([taxon for taxon in to_merge[0] if taxon in merged])

        lineages["gtdb_lineage"] = [
            s for s in lineages["gtdb_lineage"] if s is not None
        ]
        lineages["metaphlan_lineage"] = [
            s for s in lineages["metaphlan_lineage"] if s is not None
        ]

        lineages["gtdb_lineage"] = merge(lineages["gtdb_lineage"])
        lineages["metaphlan_lineage"] = merge(lineages["metaphlan_lineage"])

        return lineages

    gtdb: pl.LazyFrame = (
        pl.scan_csv(gtdb, has_header=True, infer_schema=False)
        .drop("accession", "tax_id")
        .rename({"lineage": "gtdb_lineage"})
        .unique()
    )

    metaphlan: pl.LazyFrame = (
        pl.scan_csv(metaphlan, has_header=True, infer_schema=False)
        .drop("marker")
        .rename({"lineage": "metaphlan_lineage"})
        .unique()
    )

    unmatched = query.unique(subset=["gtdb_taxonomy", "metaphlan_clade"])

    result = pl.LazyFrame(
        [],
        schema={
            "gtdb_taxonomy": pl.Utf8,
            "metaphlan_clade": pl.Utf8,
            "gtdb_lineage": pl.Utf8,
            "metaphlan_lineage": pl.Utf8,
        },
    )

    for gtdb_rank, metaphlan_rank in zip(
        reversed(GTDB_RANKS), reversed(METAPHLAN_RANKS)
    ):
        matched = (
            unmatched.join(
                gtdb,
                left_on="gtdb_taxonomy",
                right_on=gtdb_rank,
                how="left",
            )
            .join(
                metaphlan,
                left_on="metaphlan_clade",
                right_on=metaphlan_rank,
                how="left",
            )
            .select(
                [
                    "gtdb_taxonomy",
                    "metaphlan_clade",
                    "gtdb_lineage",
                    "metaphlan_lineage",
                ]
            )
        ).unique()

        unmatched = matched.filter(
            ~(
                pl.col("gtdb_lineage").is_not_null()
                & pl.col("metaphlan_lineage").is_not_null()
            )
        )

        result = pl.concat(
            [
                result,
                matched.with_columns(
                    [
                        # Update GTDB lineage if not already present
                        pl.when(
                            (pl.col("gtdb_lineage").is_not_null())
                            & (
                                ~pl.col("gtdb_taxonomy").is_in(
                                    result.collect()
                                    .filter(
                                        pl.col("gtdb_lineage").is_not_null()
                                    )["gtdb_taxonomy"]
                                    .to_list()
                                )
                            )
                        )
                        .then(pl.col("gtdb_lineage"))
                        .otherwise(None)
                        .alias("gtdb_lineage"),
                        # Update MetaPhlan lineage if not already present
                        pl.when(
                            (pl.col("metaphlan_lineage").is_not_null())
                            & (
                                ~pl.col("metaphlan_clade").is_in(
                                    result.collect()
                                    .filter(
                                        pl.col(
                                            "metaphlan_lineage"
                                        ).is_not_null()
                                    )["metaphlan_clade"]
                                    .to_list()
                                )
                            )
                        )
                        .then(pl.col("metaphlan_lineage"))
                        .otherwise(None)
                        .alias("metaphlan_lineage"),
                    ]
                ),
            ]
        )

        if (
            "family" in (gtdb_rank, metaphlan_rank)
            or unmatched.collect().height == 0
        ):
            result = pl.concat([result, unmatched])
            break
        else:
            unmatched = unmatched.select(["gtdb_taxonomy", "metaphlan_clade"])

    # find the agreement between the two lineages
    result = (
        result.group_by(["gtdb_taxonomy", "metaphlan_clade"])
        .agg(
            [
                pl.col("gtdb_lineage"),
                pl.col("metaphlan_lineage"),
            ]
        )
        .with_columns(
            pl.col("gtdb_lineage").list.unique(),
            pl.col("metaphlan_lineage").list.unique(),
        )
        .with_columns(
            merged_lineage=pl.col("gtdb_lineage")
            .list.set_intersection(pl.col("metaphlan_lineage"))
            .list.first()
        )
    ).collect()

    to_merge = result.filter(pl.col("merged_lineage").is_null()).to_dicts()

    merged = pl.LazyFrame(
        Parallel(n_jobs=-1, verbose=0)(
            delayed(reduce_lineage)(lineages) for lineages in to_merge
        )
    )

    merged = merged.with_columns(
        pl.when(pl.col("gtdb_lineage").is_null())
        .then(pl.col("metaphlan_lineage"))
        .when(pl.col("metaphlan_lineage").is_null())
        .then(pl.col("gtdb_lineage"))
        .when(
            pl.col("gtdb_lineage").str.contains(
                pl.col("metaphlan_lineage"), literal=True
            )
        )
        .then(pl.col("gtdb_lineage"))
        .when(
            pl.col("metaphlan_lineage").str.contains(
                pl.col("gtdb_lineage"), literal=True
            )
        )
        .then(pl.col("metaphlan_lineage"))
        .otherwise(pl.col("gtdb_lineage"))
        .alias("merged_lineage")
    )

    merged = pl.concat(
        [
            merged,
            result.lazy()
            .filter(pl.col("merged_lineage").is_not_null())
            .with_columns(
                pl.col("merged_lineage").alias("gtdb_lineage"),
                pl.col("merged_lineage").alias("metaphlan_lineage"),
            ),
        ]
    ).unique()

    query = query.join(
        merged,
        on=["gtdb_taxonomy", "metaphlan_clade"],
        nulls_equal=True,
        how="left",
    )

    lineage = (
        (
            pl.scan_csv(
                ncbi, has_header=True, infer_schema=False, null_values=[""]
            )
            .filter(pl.col("name_class") == "scientific name")
            .filter(
                pl.col("tax_name")
                == pl.col("lineage").str.split("|").list.last()
            )
        )
        .select("tax_id", "lineage")
        .unique(
            subset=["lineage"], keep="first"
        )  # there could be multiple tax_ids for the same lineage
    )

    query = query.join(
        lineage,
        left_on="merged_lineage",
        right_on="lineage",
        how="left",
    ).collect()

    query.write_csv(Path(out))

    return query


def get_taxonomy_from_json(file: str) -> pl.LazyFrame:
    """The function `parse_taxonomy_json` reads and processes JSON data to extract taxonomic information.

    Parameters
    ----------
    file : str
        The `file` parameter in the `parse_taxonomy_json` function is expected to be a string representing
    the path to a JSON file containing taxonomic data. The function reads and processes the JSON data
    to extract taxonomic information such as tax IDs, taxonomic names, name classes, parent IDs, and ranks.

    Returns
    -------
        The function `parse_taxonomy_json` returns a LazyFrame containing taxonomic information parsed from the
    JSON data file, including taxonomic IDs, taxonomic names, name classes, parent IDs, and ranks.

    """

    with open(Path(file)) as f:
        content = f.read()

    msp_ids = re.findall(r'"msp_id":\s*"(.*?)"', content)
    gtdbtk_anns = re.findall(r'"gtdbtk_ann":\s*"(.*?)"', content)
    metaphlan_anns = re.findall(r'"metaphlan_LM_ann":\s*"(.*?)"', content)
    metaphlan_scores = re.findall(
        r'"metaphlan_LM_ann_R2":\s*((?:"[^"]+"|[\d.]+))', content
    )

    taxa = pl.LazyFrame(
        {
            "msp_id": msp_ids,
            "gtdbtk_ann": gtdbtk_anns,
            "metaphlan_LM_ann": metaphlan_anns,
            "metaphlan_LM_ann_R": [
                score.strip('"') for score in metaphlan_scores
            ],
        }
    ).rename(
        {
            "gtdbtk_ann": "gtdb_taxonomy",
            "metaphlan_LM_ann": "metaphlan_clade",
            "metaphlan_LM_ann_R": "score",
        }
    )

    return taxa


def main():
    # Execution time for build_lineage: 4.0486 seconds
    build_lineage(parse_ncbi_taxonomy("tmp/taxdump.tar.gz"))

    # Execution time for process_gtdb_annotations: 0.4211 seconds
    process_gtdb_annotations(
        "data/GTDB",
        "tmp/taxa.csv",
        "output",
    )
    # Execution time for process_metaphlan_annotations: 0.7304 seconds
    process_metaphlan_annotations(
        "data/metaphlan/mpa_v30_CHOCOPhlAn_201901_marker_info.txt",
        "tmp/taxa.csv",
        "output",
    )

    # Execution time for merge_taxa: 3.3153 seconds
    to_merge = (
        pl.scan_csv(
            Path("data/NAR_operon_sorted/taxonomy/merged.taxa.txt"),
            separator="\t",
            has_header=False,
            infer_schema=False,
            null_values=["NA"],
        )
        .select(
            [
                pl.col("column_6").alias("gtdb_taxonomy"),
                pl.col("column_7").alias("metaphlan_clade"),
                pl.col("column_8").cast(pl.Float64).alias("score"),
            ]
        )
        .drop(["score"])
        .filter(
            ~(
                pl.col("gtdb_taxonomy").is_null()
                & pl.col("metaphlan_clade").is_null()
            )
        )
    )

    merge_taxa(
        to_merge,
        "output/gtdb.csv",
        "output/metaphlan.csv",
        ncbi="tmp/taxa.csv",
        out="output/merged.taxa.csv",
    )


if __name__ == "__main__":
    main()
