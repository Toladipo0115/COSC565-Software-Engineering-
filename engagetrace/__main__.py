"""Run with python -m engagetrace import --input-dir PATH --database PATH."""
import argparse
import json
import sys

from .importer import ImportErrorDetail, import_dataset


def main(argv=None):
    parser = argparse.ArgumentParser(description="EngageTrace local data tools")
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("import", help="Stage OULAD CSV files in SQLite")
    command.add_argument("--input-dir", required=True)
    command.add_argument("--database", default="data/engagetrace.sqlite3")
    command.add_argument("--max-file-mb", type=int, default=100)
    args = parser.parse_args(argv)
    try:
        result = import_dataset(args.input_dir, args.database, max_file_mb=args.max_file_mb)
    except ImportErrorDetail as exc:
        print(f"Import error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
