import polars as pl

from metabiome.core.matrix import SparseAbundanceMatrix
from metabiome.core.space import MetabiomeDataSpace


def make_demo_space():
    obs = pl.LazyFrame(
        pl.DataFrame({"sample": ["s1", "s2", "s3"], "age": [10, 20, 30]})
    )
    var = pl.LazyFrame(
        pl.DataFrame({"gc_id": ["gA", "gB", "gC"], "len": [100, 200, 150]})
    )
    # create a small long df
    long = pl.DataFrame(
        {
            "sample": ["s1", "s1", "s2"],
            "gc_id": ["gA", "gB", "gA"],
            "abundance": [1.0, 2.0, 3.0],
        }
    ).lazy()

    X = SparseAbundanceMatrix.from_polars(long)
    return MetabiomeDataSpace.from_filtered_data(obs=obs, X=X, var=var)


def test_space_filter_expr_on_obs():
    mds = make_demo_space()
    # filter by age > 15 should keep s2 and s3 but only s2 is in matrix
    m2 = mds[pl.col("age") > 15, :]
    assert isinstance(m2, MetabiomeDataSpace)
    assert m2.shape[0] >= 1


def test_space_obs_var_reflect_filter():
    mds = make_demo_space()
    # filter to features longer than 120 -> should keep gB only
    m2 = mds[:, pl.col("len") > 120]
    # var should now be filtered to only the matching features
    var_df = m2.var
    assert "gB" in var_df["gc_id"].to_list()
    assert "gA" not in var_df["gc_id"].to_list()
