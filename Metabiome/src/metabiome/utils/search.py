import argparse
import subprocess


def build_database(pdb_folder, db_name="pdb_database"):
    # Build Foldseek database
    cmd = ["foldseek", "createdb", pdb_folder, db_name]
    subprocess.run(cmd, check=True)
    print("Database built successfully.")


def search_database(query_pdb, db_name="pdb_database", output="results.m8"):
    # Search the database
    cmd = [
        "foldseek",
        "easy-search",
        query_pdb,
        db_name,
        output,
        "tmp/",
        "--format-output",
        "query,target,pident",
    ]
    subprocess.run(cmd, check=True)
    print(f"Search completed. Results saved in {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Build and search a PDB structure database using Foldseek."
    )
    parser.add_argument("action", choices=["build", "search"], help="Action to perform")
    parser.add_argument(
        "--pdb_folder", help="Folder containing PDB files for database building"
    )
    parser.add_argument("--query_pdb", help="Input PDB file for searching")
    parser.add_argument(
        "--db_name", default="pdb_database", help="Name of the Foldseek database"
    )
    parser.add_argument(
        "--output", default="results.m8", help="Output file for search results"
    )
    args = parser.parse_args()

    if args.action == "build" and args.pdb_folder:
        build_database(args.pdb_folder, args.db_name)
    elif args.action == "search" and args.query_pdb:
        search_database(args.query_pdb, args.db_name, args.output)
    else:
        parser.print_help()
