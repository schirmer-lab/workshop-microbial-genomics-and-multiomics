import gzip
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Literal, Union

from pydantic import BaseModel, Field, FilePath, DirectoryPath
from tqdm import tqdm


class FoldseekConfig(BaseModel):
    """Pydantic model for Foldseek configuration."""
    in_dir: DirectoryPath = Field(..., description="Input directory for protein AA sequences.")
    out_dir: Path = Field(..., description="Output directory for translated 3Di sequences.")
    executable: FilePath = Field("foldseek", description="Path to the foldseek executable.")
    extension: Literal["fasta", "faa", "fa"] = Field("fasta", description="File extension of the input sequences.")
    model_weights: Union[str, Path, None] = Field(None, description="ProstT5 model weights directory.")
    num_threads: int = Field(-1, description="Number of threads to use (-1 for all available).")


class Foldseek:
    def __init__(self, config: FoldseekConfig):
        """
        Initialize the Foldseek class with a Pydantic config object.

        Parameters
        ----------
        config : FoldseekConfig
            A Pydantic model containing all necessary configuration for Foldseek.
        """
        self.config = config
        self.threads = os.cpu_count() if self.config.num_threads == -1 else self.config.num_threads
        logging.info(f"Initialized foldseek with config: {self.config.model_dump()}")

    def run(self):
        """
        Run the Foldseek pipeline:
        1. Compress sequences from the input directory.
        2. Download the ProstT5 model weights if not provided.
        3. Create a protein database from the compressed sequences.
        4. Convert the database to 3Di format.
        """
        self.download_weights()

        if not self.in_dir.is_dir():
            raise ValueError(f"Input directory does not exist: {self.in_dir}")

        self.out_dir.mkdir(parents=True, exist_ok=True)

        with tqdm(
            self.in_dir.rglob(f"*.{self.extension}"),
            desc="Processing fasta files",
        ) as pbar:
            for fa in pbar:
                target = self.out_dir / f"{fa.stem}.3di"

                if target.exists():
                    logging.info(f"3Di file already exists: {target}")
                    pbar.update()
                    continue

                self.create_protein_database(fa)
                self.convert_db_to_3di(fa.stem)

    def download_weights(self):
        """Check or download the ProstT5 model weights."""
        if not self.model_weights:
            self.model_weights = self.out_dir / "weights"
            self.model_weights.mkdir(parents=True, exist_ok=True)

            logging.info(
                f"Downloading ProstT5 model weights to {self.model_weights}..."
            )

            cmd = [
                "foldseek",
                "databases",
                "ProstT5",
                "weights",
                str(self.model_weights),
                "--threads",
                str(self.threads),
                "--remove-tmp-files",
            ]
            try:
                subprocess.run(cmd, check=True)
                logging.info("ProstT5 model weights downloaded successfully")

            except subprocess.CalledProcessError as e:
                raise RuntimeError(
                    f"Failed to download weights: {e}\nStderr: {e.stderr}"
                )
        elif not self.model_weights.exists():
            raise ValueError(
                f"Model weights directory not found: {self.model_weights}"
            )

    def compress_sequences(self) -> Path:
        """
        Compress sequences in the given directory into a single gzipped file.
        """
        compressed = self.out_dir / f"{self.in_dir.stem}.{self.extension}.gz"

        logging.info(
            f"Compressing *.{self.extension} from {self.in_dir} into {compressed}..."
        )

        with gzip.open(compressed, "wb") as gz_out:
            for fa in sorted(self.in_dir.glob(f"*.{self.extension}")):
                with open(fa, "rb") as f_in:
                    shutil.copyfileobj(f_in, gz_out)

        logging.info(f"Sequences compressed successfully: {compressed}")
        return compressed

    def create_protein_database(self, sequence: Path):
        """
        Create a protein database from the compressed sequences using foldseek.
        The database will be created with the given name.
        """

        cmd = [
            "foldseek",
            "createdb",
            sequence.as_posix(),
            str(self.out_dir / f"{sequence.stem}"),
            "--prostt5-model",
            "weights",
            "--threads",
            str(self.threads),
        ]

        try:
            subprocess.run(cmd, check=True)
            logging.info("Protein database created successfully")

        except subprocess.CalledProcessError:
            raise RuntimeError(f"Error creating database: {cmd}")

    def convert_db_to_3di(self, database: str):
        """
        Convert the protein database to 3Di format using foldseek.
        The converted database will be saved in the output directory.
        """
        self.out_dir.mkdir(parents=True, exist_ok=True)
        logging.info(f"Converting {database} to 3Di format...")

        cmd = [
            "foldseek",
            "lndb",
            str(self.out_dir / f"{database}_h"),
            str(self.out_dir / f"{database}_ss_h"),
        ]

        try:
            subprocess.run(cmd, check=True)

        except subprocess.CalledProcessError:
            raise RuntimeError(f"Error linking headers: {cmd}")

        target = self.out_dir / f"{database}.3di"
        cmd = [
            "foldseek",
            "convert2fasta",
            str(self.out_dir / f"{database}_ss"),
            str(target),
        ]

        try:
            subprocess.run(cmd, check=True)
            logging.info(f"3Di sequences saved to {self.out_dir}")

        except subprocess.CalledProcessError:
            raise RuntimeError(f"Error converting to 3Di: {cmd}")

        finally:
            for file in self.out_dir.iterdir():
                if target.stem in file.name and file != target:
                    file.unlink()
            logging.info(f"Removed temporary files for {database}")
