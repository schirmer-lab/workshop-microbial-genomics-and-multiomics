import numpy
from Cython.Build import cythonize
from setuptools import Extension, find_packages, setup

extensions = [
    Extension(
        name="metabiome.optimized.constants",
        sources=["src/metabiome/optimized/constants.pyx"],
        include_dirs=["src/metabiome/optimized"],
    ),
    Extension(
        name="metabiome.optimized.catalog",
        sources=["src/metabiome/optimized/catalog.pyx"],
        include_dirs=["src/metabiome/optimized", numpy.get_include()],
        define_macros=[("NPY_NO_DEPRECATED_API", "NPY_1_7_API_VERSION")],
    ),
]

setup(
    name="metabiome",
    version="0.1.0",
    description="Master practicum project",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    ext_modules=cythonize(
        extensions,
        compiler_directives={
            "language_level": 3,
            "boundscheck": False,
            "wraparound": True,
            "cdivision": True,
        },
        annotate=True,
    ),
    package_data={"metabiome.optimized": ["*.pyx", "*.pxd"]},
    install_requires=[
        "cython>=3.0.0",
        "importlib>=1.0.4",
        "ipykernel>=6.29.5",
        "joblib>=1.4.2",
        "polars>=1.12.0",
        "pyarrow>=18.1.0",
        "pyfaidx>=0.8.1.3",
        "pyfamsa>=0.5.3.post1",
        "tqdm>=4.67.0",
    ],
)
