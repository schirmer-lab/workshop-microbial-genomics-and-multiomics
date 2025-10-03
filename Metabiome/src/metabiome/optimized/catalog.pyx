import numpy as np
cimport numpy as cnp
cnp.import_array()

from .constants cimport GENETIC_CODE
from libc.stdlib cimport malloc, free
from cpython.bytes cimport PyBytes_FromStringAndSize

from pyfamsa import GappedSequence

cdef inline int codon_to_index(const char* codon) nogil:
    cdef int val = 0
    for i in range(3):
        val *= 4
        if codon[i] == 84 or codon[i] == 85:
            val += 0
        elif codon[i] == 67:
            val += 1
        elif codon[i] == 65:
            val += 2
        elif codon[i] == 71:
            val += 3
        else:
            return -1
    return val

cpdef tuple codon_to_aa(bytes name, bytes sequence, int table):
    """Translate nucleotides to amino acids, return (name, aa_seq_bytes, codon_array)."""
    cdef const unsigned char[:] seq_view = sequence
    if len(seq_view) % 3 != 0:
        raise ValueError("Sequence length must be a multiple of 3.")
    cdef int n = len(seq_view) // 3

    cdef cnp.ndarray[cnp.uint8_t, ndim=2] codon_array = np.empty((n, 3), dtype=np.uint8)
    cdef cnp.ndarray[cnp.uint8_t, ndim=1] translated = np.empty(n, dtype=np.uint8)
    cdef int i, idx
    cdef char aa

    for i in range(n):
        idx = codon_to_index(<const char*>&seq_view[i*3])
        
        if idx < 0:
            raise ValueError(f"Invalid codon at position {i}: {sequence[i*3:i*3+3].decode('replace')}")
            
        aa = GENETIC_CODE[table][idx]
        translated[i] = <cnp.uint8_t>aa
        codon_array[i,0] = seq_view[i*3]
        codon_array[i,1] = seq_view[i*3+1]
        codon_array[i,2] = seq_view[i*3+2]

    return name, (<bytes>translated.tobytes()), codon_array

cpdef object classify_mutations(bytes identifier, bytes sequence, bytes consensus, int table, object buffer):
    """
    Classify non-silent mutations compared to consensus. Writes CSV lines to the provided buffer.

    Parameters
    ----------
    identifier : bytes
        Sequence identifier (as bytes).
    sequence : bytes
        Nucleotide sequence (as bytes).
    consensus : bytes
        Consensus nucleotide sequence (as bytes).
    table : int
        Genetic code table number to use for translation.
    buffer : object
        Python file-like object to write CSV lines.

    Returns
    -------
    None
        Writes output to buffer, does not return a value.
    """
    cdef int SILENT = 0
    cdef int SYNONYMOUS = 1
    cdef int INSERTION = 2
    cdef int DELETION = 3
    cdef int NONSENSE = 4
    cdef int STOPLOSS = 5
    cdef int MISSENSE = 6
    cdef int UNKNOWN = 7

    cdef char STAR = ord('*')
    cdef char GAP = ord('-')
    cdef const unsigned char[:] seq_view = sequence
    cdef const unsigned char[:] cons_view = consensus
    cdef int seq_len = len(seq_view)
    cdef int cons_len = len(cons_view)
    cdef int pos, mut_type, idx_ref, idx_var, j
    cdef char ref_aa, var_aa
    cdef tuple mt_names = (
        "silent", "synonymous", "insertion", "deletion",
        "nonsense", "stop loss", "missense", "unknown"
    )
    cdef str id_str = identifier.decode('utf-8')

    cdef bint is_consensus_gap, is_sequence_gap, ref_has_gap, var_has_gap

    for pos in range(0, seq_len, 3):
        if pos+2 >= seq_len or pos+2 >= cons_len:
            continue

        is_consensus_gap, is_sequence_gap = 1, 1

        for j in range(3):
            if cons_view[pos+j] != GAP:
                is_consensus_gap = 0
                break
        for j in range(3):
            if seq_view[pos+j] != GAP:
                is_sequence_gap = 0
                break

        if is_consensus_gap and not is_sequence_gap:
            idx_var = codon_to_index(<const char*>&seq_view[pos])
            if idx_var >= 0:
                var_aa = GENETIC_CODE[table][idx_var]
                buffer.write(f"{id_str},{pos//3 + 1},-,{chr(var_aa)},insertion\n")
            else:
                buffer.write(f"{id_str},{pos//3 + 1},-,-,insertion\n")
            continue
        elif is_sequence_gap and not is_consensus_gap:
            idx_ref = codon_to_index(<const char*>&cons_view[pos])
            if idx_ref >= 0:
                ref_aa = GENETIC_CODE[table][idx_ref]
                buffer.write(f"{id_str},{pos//3 + 1},{chr(ref_aa)},-,deletion\n")
            else:
                buffer.write(f"{id_str},{pos//3 + 1},-,-,deletion\n")
            continue
        elif is_consensus_gap and is_sequence_gap:
            continue

        idx_ref = codon_to_index(<const char*>&cons_view[pos])
        idx_var = codon_to_index(<const char*>&seq_view[pos])

        if idx_ref < 0 or idx_var < 0:
            continue

        ref_aa = GENETIC_CODE[table][idx_ref]
        var_aa = GENETIC_CODE[table][idx_var]

        ref_has_gap, var_has_gap = 0, 0

        for j in range(3):
            if cons_view[pos+j] == GAP:
                ref_has_gap = 1
            if seq_view[pos+j] == GAP:
                var_has_gap = 1

        ref_aa_str = '-' if ref_has_gap else chr(ref_aa)
        var_aa_str = '-' if var_has_gap else chr(var_aa)

        is_codon_equal = (seq_view[pos] == cons_view[pos] and
                       seq_view[pos+1] == cons_view[pos+1] and
                       seq_view[pos+2] == cons_view[pos+2])

        if is_codon_equal and ref_aa == var_aa:
            mut_type = SILENT
        elif not is_codon_equal and ref_aa == var_aa:
            mut_type = SYNONYMOUS
        elif ref_aa == GAP and var_aa != GAP:
            mut_type = INSERTION
        elif ref_aa != GAP and var_aa == GAP:
            mut_type = DELETION
        elif ref_aa != STAR and var_aa == STAR:
            mut_type = NONSENSE
        elif ref_aa == STAR and var_aa != STAR:
            mut_type = STOPLOSS
        elif ref_aa != var_aa:
            mut_type = MISSENSE
        else:
            mut_type = UNKNOWN

        if mut_type == SILENT:
            continue

        buffer.write(f"{id_str},{pos//3 + 1},{ref_aa_str},{var_aa_str},{mt_names[mut_type]}\n")
    return

cpdef object protein_to_nucleotide(object seq_id, bytes gapped_prot_seq, unsigned char[:, :] mapping):
    """Map gapped protein to nucleotide sequence via codon mapping and return a GappedSequence object (Python version)."""
    cdef Py_ssize_t i = 0, gaps = 0, size = len(gapped_prot_seq)
    cdef Py_ssize_t out_idx = 0
    cdef int dash = ord('-')
    cdef unsigned char* outbuf = <unsigned char*>malloc(3 * size)
    if outbuf == NULL:
        raise MemoryError()
    cdef unsigned char* map_ptr = &mapping[0,0]
    cdef Py_ssize_t map_stride = mapping.strides[0] // mapping.itemsize

    try:
        while i < size:
            if gapped_prot_seq[i] == dash:
                outbuf[out_idx] = dash
                outbuf[out_idx+1] = dash
                outbuf[out_idx+2] = dash
                out_idx += 3
                gaps += 1
            else:
                # Use pointer arithmetic for faster access
                base_idx = (i - gaps) * 3
                outbuf[out_idx] = map_ptr[base_idx]
                outbuf[out_idx+1] = map_ptr[base_idx+1]
                outbuf[out_idx+2] = map_ptr[base_idx+2]
                out_idx += 3
            i += 1
        py_bytes = PyBytes_FromStringAndSize(<char*>outbuf, out_idx)
        gapped_seq = GappedSequence(seq_id, py_bytes)
    finally:
        free(outbuf)
    return gapped_seq

cpdef char get_most_common_base(char[:] input_vector, float threshold, bint include_gaps):
    """Get most common base in a column, return as char (int)."""
    cdef Py_ssize_t n = input_vector.shape[0]
    cdef int[256] counts
    cdef int i, maxc = 0
    cdef int gap = ord('-')
    for i in range(256): counts[i] = 0

    for i in range(n):
        if include_gaps or input_vector[i] != gap:
            counts[<unsigned char>input_vector[i]] += 1

    cdef char mb = <char>gap

    for i in range(256):
        if counts[i] > 0 and counts[i] >= threshold*n and counts[i] > maxc:
            maxc = counts[i]; mb = <char>i

    return mb

cpdef float calculate_average_pid(char[:, :] matrix, char[:] reference) nogil:
    """Calculate average percentage identity (0.0-1.0)."""
    cdef Py_ssize_t rows = matrix.shape[0], cols = matrix.shape[1]
    cdef int matches = 0
    cdef Py_ssize_t r, c

    for c in range(cols):
        for r in range(rows):
            if matrix[r, c] == reference[c]: matches += 1

    return matches / (<float>(rows * cols))


cpdef cnp.ndarray[cnp.float32_t, ndim=1] calculate_positional_pid(char[:, :] matrix, char[:] reference):
    """Calculate percentage identity (0.0-100.0) for each position."""
    cdef Py_ssize_t rows = matrix.shape[0]
    cdef Py_ssize_t cols = matrix.shape[1]
    cdef cnp.ndarray[cnp.float32_t, ndim=1] pids = np.zeros(cols, dtype=np.float32)
    cdef int matches
    cdef Py_ssize_t r, c

    if rows == 0:
        return pids

    for c in range(cols):
        matches = 0
        for r in range(rows):
            if matrix[r, c] == reference[c]:
                matches += 1
        pids[c] = (<float>matches / <float>rows) * 100.0

    return pids
