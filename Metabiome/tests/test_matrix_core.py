import polars as pl

# minimal tests — avoid unused imports
from metabiome.core.matrix import SparseAbundanceMatrix


def make_long_df():
    df = pl.DataFrame(
        {
            "sample": ["s1", "s1", "s2", "s3"],
            "gc_id": ["gA", "gB", "gA", "gC"],
            "abundance": [1.0, 2.0, 3.0, 4.0],
        }
    )
    return df


def test_from_polars_and_shape():
    df = make_long_df()
    mat = SparseAbundanceMatrix.from_polars(df)
    assert mat.shape == (3, 3)
    assert set(mat.obs_names) == {"s1", "s2", "s3"}
    assert set(mat.var_names) == {"gA", "gB", "gC"}


def test_to_long_lazy_and_collect():
    df = make_long_df()
    mat = SparseAbundanceMatrix.from_polars(df)
    lf = mat.to_long()
    # should be a LazyFrame
    assert isinstance(lf, pl.LazyFrame)
    collected = lf.collect()
    assert set(collected["sample"].to_list()) <= set(mat.obs_names)


def test_getitem_by_names_and_positions():
    df = make_long_df()
    mat = SparseAbundanceMatrix.from_polars(df)

    # by names
    sub = mat[["s1", "s3"], ["gA", "gC"]]
    assert isinstance(sub, SparseAbundanceMatrix)
    assert sub.shape[0] == 2
    assert sub.shape[1] == 2

    # by positions
    sub2 = mat[[0, 2], [0, 2]]
    assert sub2.shape == (2, 2)
