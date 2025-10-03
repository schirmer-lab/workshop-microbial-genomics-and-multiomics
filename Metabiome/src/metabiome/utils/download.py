import re
import logging
import requests
import polars as pl
from pathlib import Path
from typing import List, Optional
from concurrent.futures import ThreadPoolExecutor
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from tqdm import tqdm

UNIPROT_BASE_URL = "https://rest.uniprot.org/uniprotkb"
PDB_BASE_URL = "https://files.rcsb.org/download"
ALPHAFOLD_BASE_URL = "https://alphafold.ebi.ac.uk/files"
MAX_WORKERS = 4
CHUNK_SIZE = 8192


def create_session() -> requests.Session:
    """Create a requests session with retry logic"""
    session = requests.Session()
    retries = Retry(
        total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504]
    )
    session.mount("https://", HTTPAdapter(max_retries=retries))
    return session


def read_identifiers(file_path: str) -> List[str]:
    """
    Read protein identifiers from file, skipping comments and empty lines.

    Args:
        file_path (str): Path to text file containing protein IDs

    Returns:
        List[str]: List of valid protein identifiers
    """
    try:
        with open(Path(file_path).resolve(), "r") as f:
            identifiers = [
                line.strip()
                for line in f
                if line.strip() and not line.strip().startswith("#")
            ]

        if not identifiers:
            raise ValueError("No valid identifiers found in input file")

        return identifiers

    except FileNotFoundError:
        raise FileNotFoundError(f"Input file not found: {file_path}")
    except PermissionError:
        raise PermissionError(f"Permission denied accessing file: {file_path}")
    except Exception as e:
        raise Exception(f"Error reading file: {str(e)}")


def download_pdb(pdb_id: str, out_dir: Path, session: requests.Session) -> None:
    """Download PDB structure file"""
    pdb_id = pdb_id.lower()
    url = f"{PDB_BASE_URL}/{pdb_id}.cif"
    response = session.get(url, stream=True)

    if response.ok:
        file_path = out_dir / f"{pdb_id}.cif"
        with open(file_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                f.write(chunk)
        return file_path
    else:
        logging.error(
            f"Unable to download PDB {pdb_id} (Status code: {response.status_code} - {response.reason})"
        )


def download_alphafold_model(
    identifier: str, out_dir: Path, session: requests.Session
) -> Optional[Path]:
    """Download AlphaFold predicted structure"""
    url = f"{ALPHAFOLD_BASE_URL}/AF-{identifier}-F1-model_v4.cif"
    response = session.get(url, stream=True)

    if response.ok:
        file_path = out_dir / f"AF-{identifier}-model_v4.cif"
        with open(file_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                f.write(chunk)
        return file_path
    else:
        logging.error(
            f"Unable to download AlphaFold model {identifier} (Status code: {response.status_code} - {response.reason})"
        )


def process_identifier(
    identifier: str, out_dir: str, session: requests.Session
) -> None:
    """Process single protein identifier"""
    try:
        if not validate_identifier(identifier):
            logging.error(f"Invalid identifier format: {identifier}")
            return

        save_dir = Path(out_dir).resolve() / identifier
        save_dir.mkdir(parents=True, exist_ok=True)

        (
            download_pdb(pdb, save_dir, session)
            if (pdb := get_best_structure(identifier, str(save_dir)))
            else logging.info(f"No PDB structures found for {identifier}")
        )

        download_alphafold_model(identifier, save_dir, session)

    except Exception as e:
        logging.error(f"Error processing identifier {identifier}: {str(e)}")


def get_best_structure(identifier: str, output_dir: str) -> Optional[str]:
    """
    Get metadata for all protein structures given a UniProt ID and return the PDB ID with best coverage.
    Returns None if no PDB structures are available.
    """
    url = f"{UNIPROT_BASE_URL}/{identifier}?format=txt"
    response = requests.get(url)

    data = []
    for line in response.text.splitlines():
        if line.startswith("DR   PDB;"):
            fields = line[10:].split(";")
            pdb = fields[0].strip()
            method = fields[1].strip()
            resolution = fields[2].split()[0]
            coverage = fields[3].rstrip(".")
            ranges = coverage.split(", ")  # for case where multiple ranges are present

            total_coverage = 0
            for r in ranges:
                start, end = map(int, r.split("=")[1].split("-"))
                length = end - start + 1
                total_coverage += length

            data.append(
                {
                    "PDB": pdb,
                    "method": method,
                    "resolution": resolution,
                    "coverage": length,
                }
            )

    if not data:
        logging.info(f"No PDB structures found for {identifier}")
        return None

    df = pl.DataFrame(data)
    out_path = Path(output_dir) / f"{identifier}_metadata.csv"
    df.write_csv(out_path)

    best = (
        df.filter(pl.col("coverage") == pl.col("coverage").max())
        .sort("resolution")
        .head(1)
    )

    return best["PDB"][0]


def validate_identifier(identifier: str) -> bool:
    """Validate UniProt ID format"""
    pattern = (
        r"^(?:[OPQ][0-9][A-Z0-9]{3}[0-9]|[A-NR-Z][0-9](?:[A-Z][A-Z0-9]{2}[0-9]){1,2})$"
    )
    return bool(re.match(pattern, identifier))


def fetch_structure(file_path: str, out_dir: str) -> None:
    """Main function to fetch protein structures"""
    session = create_session()
    identifiers = read_identifiers(file_path)

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        list(
            tqdm(
                executor.map(
                    lambda x: process_identifier(x, out_dir, session), identifiers
                ),
                total=len(identifiers),
                desc="Downloading structures",
                leave=False,
            )
        )


if __name__ == "__main__":
    fetch_structure("tmp/test.txt", "data/structures")
