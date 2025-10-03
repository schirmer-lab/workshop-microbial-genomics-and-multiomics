import asyncio
import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING

import aiofiles
import numpy as np

from ..optimized import calculate_average_pid
from .catalog import ProteinGroup

if TYPE_CHECKING:
    from metabiome.core.space import MetabiomeDataSpace


class ProteinCluster(ProteinGroup):
    """
    Represents a protein cluster identified by a representative sequence ID.

    Attributes
    ----------
    representative_id : str
        The identifier of the representative protein sequence.
    members : list[str]
        A list of all protein IDs belonging to this cluster (including the representative).
    """

    def __init__(
        self,
        mds: "MetabiomeDataSpace",
        representative_id: str,
        members: list[str],
    ):
        super().__init__(mds)
        self._representative_id = representative_id
        self._members = members

    def __call__(
        self,
        threads: int | None = None,
        threshold: float = 0.1,
    ):
        self.n_jobs = threads if threads else os.cpu_count()

        self.align_prot_seq(
            threads=self.n_jobs,
            sequences=list(self),
        )

        self.generate_consensus(threshold=threshold, key="protein")

        if "protein" not in self.alignment or not self.alignment["protein"]:
            raise RuntimeError(
                "Protein alignment missing; run align_prot_seq first."
            )

        matrix = np.stack(
            [
                np.frombuffer(record.sequence, dtype=np.int8)
                for record in self.alignment["protein"]
            ]
        )

        assert matrix.shape[1] == len(self.consensus), (
            f"Matrix shape {matrix.shape} does not match consensus length {len(self.consensus)}"
        )

        pid = calculate_average_pid(
            matrix,
            np.frombuffer(self.consensus, dtype=np.int8).copy(),
        )

        asyncio.run(self._save_annotations(pid))

    async def _save_annotations(self, pid: float) -> None:
        """
        Asynchronously saves alignment, consensus, and PID annotations to files.
        """
        await self._save_alignment()
        async with aiofiles.open(self.outdir / "consensus.fasta", "wb") as f:
            await f.write(self.consensus)
        async with aiofiles.open(self.outdir / "pid.json", "w") as f:
            await f.write(
                f'{{"cluster": "{self.representative_id}", "pid": {pid}}}'
            )

    def __iter__(self):
        """
        Iterates over the sequences of all members in the cluster.

        Yields
        ------
        Sequence
            Sequence objects for each member present in the FASTA.
        Missing members are skipped with a warning.
        """
        for member_id in self.members:
            seq = self[member_id]

            if seq is None:
                logging.warning(
                    "Member ID %s not found in the FASTA file. Skipping this member.",
                    member_id,
                )
                continue

            yield seq

    def __add__(self, members: str | list[str]) -> "ProteinCluster":
        """Adds a member protein ID to the cluster (in-place) and returns self.

        This makes `cluster + 'id'` or `cluster + ['id1', 'id2']` behave in-place
        while still returning the cluster for chaining if desired.
        """
        if isinstance(members, str):
            self._members.append(members)
        elif isinstance(members, list):
            self._members.extend(members)
        else:
            raise TypeError("Members must be a string or a list of strings.")
        return self

    def __contains__(self, member_id: str) -> bool:
        """Checks if a member protein ID is part of the cluster."""
        return member_id in self.members

    def __len__(self) -> int:
        """Returns the number of members in the cluster."""
        return len(self.members)

    def __str__(self) -> str:
        return f"ProteinCluster(Representative='{self.representative_id}', Members={len(self)})"

    def __repr__(self) -> str:
        return self.__str__()

    @property
    def representative_id(self) -> str:
        return self._representative_id

    @representative_id.setter
    def representative_id(self, representative_id: str) -> None:
        if not isinstance(representative_id, str):
            raise TypeError("Representative ID must be a string.")
        self._representative_id = representative_id

    @property
    def members(self) -> list[str]:
        return self._members

    @members.setter
    def members(self, members: list[str]) -> None:
        if not isinstance(members, list):
            raise TypeError("Members must be a list.")
        self._members = members

    @property
    def outdir(self) -> Path:
        path = self._mds.outdir / self.representative_id
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
        return path
