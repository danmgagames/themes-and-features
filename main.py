"""
Game Enrichment Pipeline — CLI entry point.

Usage:
    python main.py extract --input POWERPOINTS [--output data/raw_extracts]
    python main.py classify [--dry-run]
    python main.py consolidate
    python main.py merge-review
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / '.env')


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


def cmd_classify(args):
    """Phase 2: Classify themes and features for all extracted games."""
    import anthropic
    from agents.theme_classifier import classify_theme
    from agents.feature_classifier import classify_features
    from agents.localisation_resolver import (
        load_market_db, build_game_families, detect_celebrity_ips, match_extract_to_family,
    )

    extracts_dir = Path(args.extracts).resolve() if args.extracts else PROJECT_ROOT / 'data' / 'raw_extracts'
    output_dir = Path(args.output).resolve() if args.output else PROJECT_ROOT / 'data' / 'classified'
    market_path = Path(args.market_names).resolve() if args.market_names else PROJECT_ROOT / 'config' / 'market_names.xlsx'
    taxonomy_path = PROJECT_ROOT / 'config' / 'seo_taxonomy.json'
    log_path = PROJECT_ROOT / 'data' / 'classifier_log.jsonl'

    if not extracts_dir.exists():
        print(f"Error: Extracts folder not found: {extracts_dir}")
        sys.exit(1)

    if not taxonomy_path.exists():
        print(f"Error: Taxonomy file not found: {taxonomy_path}")
        sys.exit(1)

    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        print("Error: ANTHROPIC_API_KEY not set. Add it to .env or export it.")
        sys.exit(1)

    # Load taxonomy
    with open(taxonomy_path, 'r', encoding='utf-8') as f:
        taxonomy = json.load(f)

    # Load extracts
    extract_files = sorted(extracts_dir.glob('*.json'))
    if args.dry_run:
        extract_files = extract_files[:5]
        print(f"DRY RUN: processing first {len(extract_files)} games only\n")

    extracts = []
    for ef in extract_files:
        with open(ef, 'r', encoding='utf-8') as f:
            extracts.append(json.load(f))

    print(f"Extracts loaded:  {len(extracts)}")

    # Load market DB and build families
    families = {}
    if market_path.exists():
        market_rows = load_market_db(market_path)
        families = build_game_families(market_rows, include_deactivated=args.include_deactivated)
        detect_celebrity_ips(families)
        print(f"Game families:    {len(families)}")
    else:
        print("Market DB:        not found (skipping localisation)")

    output_dir.mkdir(parents=True, exist_ok=True)

    # Run async classification
    max_concurrent = 10
    client = anthropic.AsyncAnthropic(api_key=api_key)

    async def classify_one(extract):
        base_key = extract.get('base_key', 'unknown')

        # Run theme + feature classification in parallel
        theme_result, feature_result = await asyncio.gather(
            classify_theme(extract, taxonomy, client),
            classify_features(extract, taxonomy, client),
        )

        # Localisation resolution (deterministic, no API call)
        loc_result = match_extract_to_family(extract, families) if families else {
            'base_key': None,
            'es_commercial_name': None,
            'category': extract.get('folder_category'),
            'markets': [],
            'celebrity_names': [],
            'match_confidence': 0.0,
            'match_method': 'skipped',
        }

        # If celebrity detected, add Celebrities theme
        if loc_result['celebrity_names'] and 'Celebrities' not in theme_result['themes']:
            theme_result['themes'].append('Celebrities')
            for name in loc_result['celebrity_names']:
                if name not in theme_result['themes']:
                    theme_result['themes'].append(name)

        combined = {
            'base_key': loc_result['base_key'] or base_key,
            'folder_game_name': extract.get('folder_game_name'),
            'folder_category': extract.get('folder_category'),
            'pptx_found': extract.get('pptx_found', False),
            'es_commercial_name': loc_result.get('es_commercial_name'),
            'category': loc_result.get('category') or extract.get('folder_category'),
            'markets': loc_result.get('markets', []),
            'celebrity_names': loc_result.get('celebrity_names', []),
            'localisation_match_confidence': loc_result.get('match_confidence', 0.0),
            'localisation_match_method': loc_result.get('match_method'),
            'themes': theme_result['themes'],
            'theme_confidence': theme_result['confidence'],
            'theme_reasoning': theme_result['reasoning'],
            'theme_error': theme_result.get('error'),
            'features': feature_result['features'],
            'unknown_features': feature_result.get('unknown_features', []),
            'feature_confidence': feature_result['confidence'],
            'feature_reasoning': feature_result['reasoning'],
            'feature_error': feature_result.get('error'),
        }

        return combined

    async def run_all():
        semaphore = asyncio.Semaphore(max_concurrent)
        results = []
        completed = 0

        async def limited(extract):
            nonlocal completed
            async with semaphore:
                result = await classify_one(extract)
                completed += 1
                status = "OK" if not result.get('theme_error') and not result.get('feature_error') else "ERR"
                print(f"  [{completed}/{len(extracts)}] {result['base_key']}: {status} "
                      f"({len(result['themes'])} themes, {len(result['features'])} features)")
                return result

        results = await asyncio.gather(*[limited(e) for e in extracts])
        return results

    print(f"\nClassifying with max {max_concurrent} concurrent API calls...\n")
    results = asyncio.run(run_all())

    # Write individual classified JSONs
    for result in results:
        safe_name = result['base_key'].replace(' ', '_')
        safe_name = ''.join(c if c.isalnum() or c in ('_', '-') else '_' for c in safe_name)
        output_path = output_dir / f"{safe_name}.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

    # Append to classifier log
    with open(log_path, 'a', encoding='utf-8') as f:
        for result in results:
            f.write(json.dumps(result, ensure_ascii=False) + '\n')

    # Summary
    theme_errors = sum(1 for r in results if r.get('theme_error'))
    feature_errors = sum(1 for r in results if r.get('feature_error'))
    all_unknown = []
    for r in results:
        all_unknown.extend(r.get('unknown_features', []))

    print()
    print("=" * 50)
    print("Classification complete")
    print("=" * 50)
    print(f"  Games classified:   {len(results)}")
    print(f"  Theme errors:       {theme_errors}")
    print(f"  Feature errors:     {feature_errors}")
    if all_unknown:
        unique_unknown = sorted(set(all_unknown))
        print(f"  Unknown features:   {len(unique_unknown)}")
        for uf in unique_unknown:
            print(f"    - {uf}")
    print(f"  Output written to:  {output_dir}")
    print(f"  Log appended to:    {log_path}")


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

    # classify
    p_classify = subparsers.add_parser('classify', help='Phase 2: Classify themes and features')
    p_classify.add_argument('--extracts', '-e', default=None, help='Path to raw extracts dir (default: data/raw_extracts)')
    p_classify.add_argument('--output', '-o', default=None, help='Output dir (default: data/classified)')
    p_classify.add_argument('--market-names', '-m', default=None, help='Path to market_names.xlsx (default: config/market_names.xlsx)')
    p_classify.add_argument('--dry-run', action='store_true', help='Process first 5 games only')
    p_classify.add_argument('--include-deactivated', action='store_true', help='Include deactivated games')
    p_classify.set_defaults(func=cmd_classify)

    # Placeholder subcommands for future phases
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
