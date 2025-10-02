from pyfaidx import Fasta

from metabiome.annotations.catalog import GeneCatalog


def test_annotation():
    annotation = GeneCatalog(
        reader=Fasta(
            "data/msa/demo_narG.ecoli.mcpc_id.gc_seq.fna", read_long_names=True
        ),
        outdir="tmp",
    )

    annotation(format="csv")
