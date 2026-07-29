#!/usr/bin/env bash
# =============================================================================
# Repack the course data archive, smaller, without touching a single notebook.
#
#   ./scripts/repack_resources.sh --input resources-251007_2200.zip \
#                                 --output resources-$(date +%y%m%d).zip
#
# The current archive (Zenodo record 17285503) is 1.9 GB compressed / 2.2 GB raw
# across 1084 entries. This script removes ~500 MB of it without changing any
# path that a notebook reads:
#
#   ~329 MB  day3_lab5/raw_reads/25748_R{1,2}.fastq.gz are byte-identical to
#            day2_lab2/raw_reads/25748_R{1,2}.fastq.gz (verified by CRC in the
#            zip index). Replaced with relative symlinks. day3_lab5 cell 4
#            checks them with os.path.exists(), which follows symlinks, and
#            nothing ever writes into resources_dir -- so this is transparent.
#
#   ~159 MB  day2_MSD/ is orphaned: no notebook references it. Removed by
#            default; keep it with --keep-msd.
#
#   ~small   __MACOSX/ (541 entries) and .DS_Store files.
#
# NOT done here, because it would require editing a notebook:
#
#   ~779 MB  day1_lab2/mgx_reads/PSMB4MBK_R{1,2}.fastq.gz are downloaded so that
#            day1_lab2 can run `ls -lh`, `zcat | head -n 4` and `zcat | wc -l`
#            on them. Subset files (PSMB4MBK_subset_R{1,2}.fastq.gz, ~480 KB
#            each) already exist in the same directory and are unused. Switching
#            to them saves 40% of the whole archive, but changes the line count
#            printed in cells 7-8.
#
# After repacking, upload as a NEW VERSION of the Zenodo record and update
# ZENODO_URL in .devcontainer/download_biodata.sh. The old URL keeps working, so
# this is reversible.
# =============================================================================

set -euo pipefail

INPUT=""
OUTPUT=""
WORKDIR=""
KEEP_MSD=false
DO_DEDUP=true
KEEP_WORKDIR=false

# ANSI-C quoting so the codes are real escape characters and survive `cat`/heredocs.
RED=$'\033[0;31m'; GREEN=$'\033[0;32m'; YELLOW=$'\033[1;33m'; BLUE=$'\033[0;34m'; NC=$'\033[0m'

usage() {
    cat <<'EOF'
Usage: ./scripts/repack_resources.sh --input <zip|dir> --output <zip> [OPTIONS]

Required:
  -i, --input PATH     Source resources zip, or an already-extracted directory
                       containing resources/
  -o, --output PATH    Destination zip to write

Options:
      --keep-msd       Keep day2_MSD/ (default: remove, no notebook uses it)
      --no-dedup       Do not symlink the duplicated day3_lab5 raw reads
      --keep-workdir   Leave the staging directory in place for inspection
  -h, --help           Show this message

The script never modifies the input.
EOF
}

while [[ $# -gt 0 ]]; do
    case $1 in
        -i|--input)     INPUT="$2"; shift 2 ;;
        -o|--output)    OUTPUT="$2"; shift 2 ;;
        --keep-msd)     KEEP_MSD=true; shift ;;
        --no-dedup)     DO_DEDUP=false; shift ;;
        --keep-workdir) KEEP_WORKDIR=true; shift ;;
        -h|--help)      usage; exit 0 ;;
        *) echo -e "${RED}Unknown option: $1${NC}" >&2; usage >&2; exit 1 ;;
    esac
done

if [ -z "$INPUT" ] || [ -z "$OUTPUT" ]; then
    echo -e "${RED}--input and --output are required${NC}" >&2
    usage >&2
    exit 1
fi

if [ -e "$OUTPUT" ]; then
    echo -e "${RED}Refusing to overwrite existing output: $OUTPUT${NC}" >&2
    exit 1
fi

for tool in zip unzip find; do
    command -v "$tool" >/dev/null 2>&1 || { echo -e "${RED}Missing required tool: $tool${NC}" >&2; exit 1; }
done

if command -v sha256sum >/dev/null 2>&1; then
    SHA() { sha256sum "$1" | cut -d' ' -f1; }
elif command -v shasum >/dev/null 2>&1; then
    SHA() { shasum -a 256 "$1" | cut -d' ' -f1; }
else
    echo -e "${RED}Need sha256sum or shasum${NC}" >&2; exit 1
fi

human() { du -sh "$1" 2>/dev/null | cut -f1; }

cleanup() {
    if [ -n "$WORKDIR" ] && [ -d "$WORKDIR" ] && ! $KEEP_WORKDIR; then
        rm -rf "$WORKDIR"
    fi
}
trap cleanup EXIT

# --- stage -----------------------------------------------------------------

WORKDIR="$(mktemp -d)"
STAGE="$WORKDIR/stage"
mkdir -p "$STAGE"

echo -e "${BLUE}Staging input...${NC}"
if [ -d "$INPUT" ]; then
    [ -d "$INPUT/resources" ] || { echo -e "${RED}$INPUT does not contain a resources/ directory${NC}" >&2; exit 1; }
    cp -a "$INPUT/resources" "$STAGE/resources"
else
    unzip -q "$INPUT" -d "$STAGE"
    [ -d "$STAGE/resources" ] || { echo -e "${RED}Archive does not contain a top-level resources/ directory${NC}" >&2; exit 1; }
fi

SIZE_BEFORE="$(human "$STAGE")"
echo "  staged: $SIZE_BEFORE"

R="$STAGE/resources"

# --- 1. macOS cruft --------------------------------------------------------

echo -e "\n${BLUE}1. Removing macOS metadata...${NC}"
N_MACOSX=$(find "$STAGE" -name '__MACOSX' -type d | wc -l | tr -d ' ')
N_DSSTORE=$(find "$STAGE" -name '.DS_Store' | wc -l | tr -d ' ')
find "$STAGE" -name '__MACOSX' -type d -prune -exec rm -rf {} + 2>/dev/null || true
find "$STAGE" -name '.DS_Store' -delete 2>/dev/null || true
find "$STAGE" -name '._*' -delete 2>/dev/null || true
echo "  removed $N_MACOSX __MACOSX dir(s), $N_DSSTORE .DS_Store file(s)"

# A failed Google Drive download that got archived as if it were data: 212 KB of
# HTML sitting in the profile directory. No notebook references it.
STRAY_HTML="$R/day1_lab2/reference_based_metagenomic_analysis/profile/file_list.txt"
if [ -f "$STRAY_HTML" ] && head -c 15 "$STRAY_HTML" | grep -qi '<!DOCTYPE html'; then
    rm -f "$STRAY_HTML"
    echo "  removed profile/file_list.txt (a saved Google Drive error page, not data)"
fi

# --- 2. orphaned day2_MSD --------------------------------------------------

echo -e "\n${BLUE}2. Orphaned resource directories...${NC}"
if $KEEP_MSD; then
    echo -e "  ${YELLOW}keeping day2_MSD (--keep-msd)${NC}"
elif [ -d "$R/day2_MSD" ]; then
    echo "  removing day2_MSD ($(human "$R/day2_MSD")) -- no notebook references it"
    rm -rf "$R/day2_MSD"
else
    echo "  day2_MSD not present"
fi

# --- 3. deduplicate the shared Illumina reads ------------------------------

echo -e "\n${BLUE}3. Deduplicating raw reads...${NC}"
if ! $DO_DEDUP; then
    echo -e "  ${YELLOW}skipped (--no-dedup)${NC}"
else
    for name in 25748_R1.fastq.gz 25748_R2.fastq.gz; do
        src="$R/day2_lab2/raw_reads/$name"     # canonical copy
        dup="$R/day3_lab5/raw_reads/$name"     # becomes a symlink

        if [ ! -f "$src" ] || [ ! -f "$dup" ]; then
            echo -e "  ${YELLOW}skip $name: one of the two copies is missing${NC}"
            continue
        fi
        if [ -L "$dup" ]; then
            echo "  $name already a symlink"
            continue
        fi

        # Only ever replace a file we have proven identical.
        if [ "$(SHA "$src")" = "$(SHA "$dup")" ]; then
            rm -f "$dup"
            ln -s "../../day2_lab2/raw_reads/$name" "$dup"
            echo "  $name -> symlink (saved $(du -h "$src" | cut -f1))"
        else
            echo -e "  ${RED}$name differs between day2_lab2 and day3_lab5 -- left alone${NC}"
        fi
    done
fi

# --- 4. make the precomputed MetaPhlAn profiles readable by MetaPhlAn 4 ----

echo -e "\n${BLUE}4. Normalising precomputed MetaPhlAn profiles...${NC}"
# Every data row in these files ends with a tab, so they carry 4 fields against
# a 3-name header. MetaPhlAn 3's merge_metaphlan_tables.py tolerates that;
# MetaPhlAn 4's rejects it outright:
#   ValueError: Number of passed names did not match number of header fields
# day1_lab2 cell 26 merges these files, so this archive has to be published
# before an image carrying metaphlan 4 is released.
PROFILE_DIR="$R/day1_lab2/reference_based_metagenomic_analysis/profile"
TAB="$(printf '\t')"
if [ -d "$PROFILE_DIR" ]; then
    FIXED=0
    for f in "$PROFILE_DIR"/*.txt; do
        [ -f "$f" ] || continue
        if grep -q "${TAB}\$" "$f" 2>/dev/null; then
            sed "s/${TAB}*\$//" "$f" > "$f.tmp$$" && mv "$f.tmp$$" "$f"
            FIXED=$((FIXED + 1))
            echo "  stripped trailing tabs: $(basename "$f")"
        fi
    done
    [ "$FIXED" -eq 0 ] && echo "  profiles already clean"
else
    echo -e "  ${YELLOW}profile directory not found -- skipped${NC}"
fi

# --- 5. validate the paths notebooks depend on -----------------------------

echo -e "\n${BLUE}5. Validating notebook resource contract...${NC}"
REQUIRED=(
    "day1_lab2/mgx_reads/PSMB4MBK_R1.fastq.gz"
    "day1_lab2/mgx_reads/PSMB4MBK_R2.fastq.gz"
    "day1_lab2/Metaphlan3_DB"
    "day1_lab2/reference_based_metagenomic_analysis/profile"
    "day1_lab3"
    "day2_lab1"
    "day2_lab2/raw_reads/25748_R1.fastq.gz"
    "day2_lab2/raw_reads/25748_R2.fastq.gz"
    "day3_lab1"
    "day3_lab2"
    "day3_lab3"
    "day3_lab4"
    "day3_lab5/raw_reads/ONT.fastq.gz"
    "day3_lab5/raw_reads/25748_R1.fastq.gz"
    "day3_lab5/raw_reads/25748_R2.fastq.gz"
    "day3_lab5/fastqc/fastqc_R1.png"
    "day3_lab5/graphs/assembly_graph_spades.png"
    "day3_lab5/checkm"
    "day3_lab5/prokka"
)
MISSING=0
for p in "${REQUIRED[@]}"; do
    # -e follows symlinks, matching os.path.exists() in day3_lab5 cell 4.
    if [ -e "$R/$p" ]; then
        printf '  \342\234\205 %s\n' "$p"
    else
        printf '  \342\235\214 %s\n' "$p"
        MISSING=$((MISSING + 1))
    fi
done

if [ "$MISSING" -gt 0 ]; then
    echo -e "\n${RED}$MISSING required path(s) missing -- not writing an archive.${NC}" >&2
    exit 1
fi

# --- 6. repack -------------------------------------------------------------

echo -e "\n${BLUE}6. Writing archive...${NC}"
SIZE_AFTER="$(human "$STAGE")"

OUT_ABS="$(cd "$(dirname "$OUTPUT")" && pwd)/$(basename "$OUTPUT")"
(
    cd "$STAGE"
    # -y store symlinks as links (do NOT follow them, that would undo the dedup)
    # -X drop extra file attributes
    # -r recurse
    zip -q -r -y -X "$OUT_ABS" resources
)

echo ""
echo -e "${GREEN}Done.${NC}"
printf '  staged before : %s\n' "$SIZE_BEFORE"
printf '  staged after  : %s\n' "$SIZE_AFTER"
printf '  archive       : %s (%s)\n' "$OUTPUT" "$(human "$OUT_ABS")"

cat <<EOF

${BLUE}Next steps${NC}
  1. Spot-check:  unzip -l "$OUTPUT" | head -30
     Symlinked entries show a size of 0 with an 'l' type in \`unzip -Z\`.
  2. Upload as a NEW VERSION of Zenodo record 17285503.
  3. Update ZENODO_URL in .devcontainer/download_biodata.sh.
  4. Rebuild the dev container from scratch (rm -rf ~/biodata/resources first)
     and run every notebook.
EOF
