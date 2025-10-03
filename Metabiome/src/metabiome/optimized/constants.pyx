cdef dict IUPAC = {
    b"A": b"A", b"C": b"C", b"G": b"G", b"T": b"T", b"U": b"U", b"-": b"-",
    frozenset([b"A", b"G"]): b"R", frozenset([b"C", b"T"]): b"Y",
    frozenset([b"G", b"C"]): b"S", frozenset([b"A", b"T"]): b"W",
    frozenset([b"G", b"T"]): b"K", frozenset([b"A", b"C"]): b"M",
    frozenset([b"C", b"G", b"T"]): b"B", frozenset([b"A", b"G", b"T"]): b"D",
    frozenset([b"A", b"C", b"T"]): b"H", frozenset([b"A", b"C", b"G"]): b"V",
    frozenset([b"A", b"C", b"G", b"T"]): b"N",
    b"R": b"R", b"N": b"N", b"D": b"D", b"Q": b"Q", b"E": b"E", b"H": b"H",
    b"I": b"I", b"L": b"L", b"K": b"K", b"M": b"M", b"F": b"F", b"P": b"P",
    b"S": b"S", b"W": b"W", b"Y": b"Y", b"V": b"V", b"O": b"O", b"*": b"*",
    b"X": b"X",
    frozenset([b"D", b"N"]): b"B", frozenset([b"E", b"Q"]): b"Z",
    frozenset([b"I", b"L"]): b"J",
    frozenset([
        b"A", b"R", b"N", b"D", b"C", b"Q", b"E", b"G", b"H", b"I",
        b"L", b"K", b"M", b"F", b"P", b"S", b"T", b"W", b"Y", b"V"
    ]): b"X",
}


# The GENETIC_CODE array below is indexed by NCBI table number, so that GENETIC_CODE[table_number][codon_index] gives the one-letter amino acid code for a codon in that table.
# If a table is not present, its row should be filled with a default (e.g., all '*').
# The codon index is in base-4 order: T=0, C=1, A=2, G=3 for each position (left to right).

cdef char[12][64] GENETIC_CODE = [
    # Table 0: unused (fill with stop codons for safety)
    [
        b'*', b'*', b'*', b'*', b'*', b'*', b'*', b'*',
        b'*', b'*', b'*', b'*', b'*', b'*', b'*', b'*',
        b'*', b'*', b'*', b'*', b'*', b'*', b'*', b'*',
        b'*', b'*', b'*', b'*', b'*', b'*', b'*', b'*',
        b'*', b'*', b'*', b'*', b'*', b'*', b'*', b'*',
        b'*', b'*', b'*', b'*', b'*', b'*', b'*', b'*',
        b'*', b'*', b'*', b'*', b'*', b'*', b'*', b'*',
        b'*', b'*', b'*', b'*', b'*', b'*', b'*', b'*'
    ],
    # Table 1: Standard
    [
        b'F', b'F', b'L', b'L', b'S', b'S', b'S', b'S',
        b'Y', b'Y', b'*', b'*', b'C', b'C', b'*', b'W',
        b'L', b'L', b'L', b'L', b'P', b'P', b'P', b'P',
        b'H', b'H', b'Q', b'Q', b'R', b'R', b'R', b'R',
        b'I', b'I', b'I', b'M', b'T', b'T', b'T', b'T',
        b'N', b'N', b'K', b'K', b'S', b'S', b'R', b'R',
        b'V', b'V', b'V', b'V', b'A', b'A', b'A', b'A',
        b'D', b'D', b'E', b'E', b'G', b'G', b'G', b'G'
    ],
    # Table 2: Vertebrate Mitochondrial
    [
        b'F', b'F', b'L', b'L', b'S', b'S', b'S', b'S',
        b'Y', b'Y', b'*', b'*', b'C', b'C', b'W', b'W',
        b'L', b'L', b'L', b'L', b'P', b'P', b'P', b'P',
        b'H', b'H', b'Q', b'Q', b'R', b'R', b'R', b'R',
        b'I', b'I', b'M', b'M', b'T', b'T', b'T', b'T',
        b'N', b'N', b'K', b'K', b'S', b'S', b'*', b'*',
        b'V', b'V', b'V', b'V', b'A', b'A', b'A', b'A',
        b'D', b'D', b'E', b'E', b'G', b'G', b'G', b'G'
    ],
    # Table 3: Yeast Mitochondrial
    [
        b'F', b'F', b'L', b'L', b'S', b'S', b'S', b'S',
        b'Y', b'Y', b'*', b'*', b'C', b'C', b'W', b'W',
        b'T', b'T', b'T', b'T', b'P', b'P', b'P', b'P',
        b'H', b'H', b'Q', b'Q', b'R', b'R', b'R', b'R',
        b'I', b'I', b'M', b'M', b'T', b'T', b'T', b'T',
        b'N', b'N', b'K', b'K', b'S', b'S', b'R', b'R',
        b'V', b'V', b'V', b'V', b'A', b'A', b'A', b'A',
        b'D', b'D', b'E', b'E', b'G', b'G', b'G', b'G'
    ],
    # Table 4: Mold, Protozoan, Coelenterate Mitochondrial and Mycoplasma/Spiroplasma
    [
        b'F', b'F', b'L', b'L', b'S', b'S', b'S', b'S',
        b'Y', b'Y', b'*', b'*', b'C', b'C', b'W', b'W',
        b'L', b'L', b'L', b'L', b'P', b'P', b'P', b'P',
        b'H', b'H', b'Q', b'Q', b'R', b'R', b'R', b'R',
        b'I', b'I', b'I', b'M', b'T', b'T', b'T', b'T',
        b'N', b'N', b'K', b'K', b'S', b'S', b'R', b'R',
        b'V', b'V', b'V', b'V', b'A', b'A', b'A', b'A',
        b'D', b'D', b'E', b'E', b'G', b'G', b'G', b'G'
    ],
    # Table 5: Invertebrate Mitochondrial
    [
        b'F', b'F', b'L', b'L', b'S', b'S', b'S', b'S',
        b'Y', b'Y', b'*', b'*', b'C', b'C', b'W', b'W',
        b'L', b'L', b'L', b'L', b'P', b'P', b'P', b'P',
        b'H', b'H', b'Q', b'Q', b'R', b'R', b'R', b'R',
        b'I', b'I', b'M', b'M', b'T', b'T', b'T', b'T',
        b'N', b'N', b'K', b'K', b'S', b'S', b'S', b'S',
        b'V', b'V', b'V', b'V', b'A', b'A', b'A', b'A',
        b'D', b'D', b'E', b'E', b'G', b'G', b'G', b'G'
    ],
    # Table 6: Ciliate, Dasycladacean and Hexamita Nuclear
    [
        b'F', b'F', b'L', b'L', b'S', b'S', b'S', b'S',
        b'Y', b'Y', b'Q', b'Q', b'C', b'C', b'*', b'W',
        b'L', b'L', b'L', b'L', b'P', b'P', b'P', b'P',
        b'H', b'H', b'Q', b'Q', b'R', b'R', b'R', b'R',
        b'I', b'I', b'I', b'M', b'T', b'T', b'T', b'T',
        b'N', b'N', b'K', b'K', b'S', b'S', b'R', b'R',
        b'V', b'V', b'V', b'V', b'A', b'A', b'A', b'A',
        b'D', b'D', b'E', b'E', b'G', b'G', b'G', b'G'
    ],
    # Table 7, 8: unused (fill with stop codons)
    [
        b'*', b'*', b'*', b'*', b'*', b'*', b'*', b'*',
        b'*', b'*', b'*', b'*', b'*', b'*', b'*', b'*',
        b'*', b'*', b'*', b'*', b'*', b'*', b'*', b'*',
        b'*', b'*', b'*', b'*', b'*', b'*', b'*', b'*',
        b'*', b'*', b'*', b'*', b'*', b'*', b'*', b'*',
        b'*', b'*', b'*', b'*', b'*', b'*', b'*', b'*',
        b'*', b'*', b'*', b'*', b'*', b'*', b'*', b'*',
        b'*', b'*', b'*', b'*', b'*', b'*', b'*', b'*'
    ],
    [
        b'*', b'*', b'*', b'*', b'*', b'*', b'*', b'*',
        b'*', b'*', b'*', b'*', b'*', b'*', b'*', b'*',
        b'*', b'*', b'*', b'*', b'*', b'*', b'*', b'*',
        b'*', b'*', b'*', b'*', b'*', b'*', b'*', b'*',
        b'*', b'*', b'*', b'*', b'*', b'*', b'*', b'*',
        b'*', b'*', b'*', b'*', b'*', b'*', b'*', b'*',
        b'*', b'*', b'*', b'*', b'*', b'*', b'*', b'*',
        b'*', b'*', b'*', b'*', b'*', b'*', b'*', b'*'
    ],
    # Table 9: Echinoderm and Flatworm Mitochondrial
    [
        b'F', b'F', b'L', b'L', b'S', b'S', b'S', b'S',
        b'Y', b'Y', b'*', b'*', b'C', b'C', b'W', b'W',
        b'L', b'L', b'L', b'L', b'P', b'P', b'P', b'P',
        b'H', b'H', b'Q', b'Q', b'R', b'R', b'R', b'R',
        b'I', b'I', b'I', b'M', b'T', b'T', b'T', b'T',
        b'N', b'N', b'N', b'K', b'S', b'S', b'S', b'S',
        b'V', b'V', b'V', b'V', b'A', b'A', b'A', b'A',
        b'D', b'D', b'E', b'E', b'G', b'G', b'G', b'G'
    ],
    # Table 10: Euplotid Nuclear
    [
        b'F', b'F', b'L', b'L', b'S', b'S', b'S', b'S',
        b'Y', b'Y', b'*', b'*', b'C', b'C', b'C', b'W',
        b'L', b'L', b'L', b'L', b'P', b'P', b'P', b'P',
        b'H', b'H', b'Q', b'Q', b'R', b'R', b'R', b'R',
        b'I', b'I', b'I', b'M', b'T', b'T', b'T', b'T',
        b'N', b'N', b'K', b'K', b'S', b'S', b'R', b'R',
        b'V', b'V', b'V', b'V', b'A', b'A', b'A', b'A',
        b'D', b'D', b'E', b'E', b'G', b'G', b'G', b'G'
    ],
    # Table 11: Bacterial, Archaeal and Plant Plastid
    [
        b'F', b'F', b'L', b'L', b'S', b'S', b'S', b'S',
        b'Y', b'Y', b'*', b'*', b'C', b'C', b'*', b'W',
        b'L', b'L', b'L', b'L', b'P', b'P', b'P', b'P',
        b'H', b'H', b'Q', b'Q', b'R', b'R', b'R', b'R',
        b'I', b'I', b'I', b'M', b'T', b'T', b'T', b'T',
        b'N', b'N', b'K', b'K', b'S', b'S', b'R', b'R',
        b'V', b'V', b'V', b'V', b'A', b'A', b'A', b'A',
        b'D', b'D', b'E', b'E', b'G', b'G', b'G', b'G'
    ]
]
