"""
Game Enrichment Pipeline — CLI entry point.

Usage:
    python main.py extract --input POWERPOINTS [--output data/raw_extracts]
    python main.py classify [--dry-run]
    python main.py consolidate
    python main.py merge-review
"""

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent


def cmd_extract(args):
    """Phase 1: Extract text from PPTXs, write one JSON per game."""
    from agents.extractor import extract_all

    pptx_root = Path(args.input).resolve()
    output_dir = Path(args.output).resolve() if args.output else PROJECT_ROOT / 'data' / 'raw_extracts'
    market_path = Path(args.market_names).resolve() if args.market_names else PROJECT_ROOT / 'config' / 'market_names.xlsx'

    if not pptx_root.exists():
        print(f"Error: PPTX folder not found: {pptx_root}")
        sys.exit(1)

    print(f"Extracting from: {pptx_root}")
    print(f"Output to:       {output_dir}")
    if market_path.exists():
        print(f"Market DB:       {market_path}")
    else:
        print(f"Market DB:       not found (skipping market lookup)")
    print()

    stats = extract_all(pptx_root, market_path, output_dir)

    print()
    print("=" * 50)
    print("Extraction complete")
    print("=" * 50)
    print(f"  Game folders found:  {stats['total_folders']}")
    print(f"  PPTXs found:         {stats['pptx_found']}")
    print(f"  PPTXs not found:     {stats['pptx_not_found']}")
    if stats['market_skipped'] == 0:
        print(f"  Market exact match:  {stats['market_exact']}")
        print(f"  Market fuzzy match:  {stats['market_fuzzy']}")
        print(f"  Market no match:     {stats['market_none']}")
    else:
        print(f"  Market lookup:       skipped (no market_names.xlsx)")
    print(f"  JSON files written:  {stats['json_written']}")
    if stats['errors'] > 0:
        print(f"  Errors:              {stats['errors']}")


def main():
    parser = argparse.ArgumentParser(
        description='Game Enrichment Pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest='command', help='Pipeline phase to run')

    # extract
    p_extract = subparsers.add_parser('extract', help='Phase 1: Extract text from PPTXs')
    p_extract.add_argument('--input', '-i', required=True, help='Path to PPTX folder root')
    p_extract.add_argument('--output', '-o', default=None, help='Output dir (default: data/raw_extracts)')
    p_extract.add_argument('--market-names', '-m', default=None, help='Path to market_names.xlsx (default: config/market_names.xlsx)')
    p_extract.set_defaults(func=cmd_extract)

    # Placeholder subcommands for future phases
    subparsers.add_parser('classify', help='Phase 2: Classify themes and features (not yet implemented)')
    subparsers.add_parser('consolidate', help='Phase 3: Consolidate and output CSV (not yet implemented)')
    subparsers.add_parser('merge-review', help='Merge reviewed CSV back (not yet implemented)')

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    if not hasattr(args, 'func'):
        print(f"Command '{args.command}' is not yet implemented.")
        sys.exit(1)

    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    args.func(args)


if __name__ == '__main__':
    main()
