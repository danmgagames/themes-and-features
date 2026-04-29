"""
Merge data/classified_8/<base_key>.json into data/classified/<base_key>.json.

Web-sourced classified files have the full schema needed by consolidator
(base_key + themes + features + description + web_found + web_source_language).
We just need to copy them over so `consolidate` picks them up.

Refuses to overwrite an existing classified/ file unless --force is passed.
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / 'data' / 'classified_8'
DST_DIR = PROJECT_ROOT / 'data' / 'classified'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--force', action='store_true',
                    help='Overwrite existing classified/<base_key>.json files')
    ap.add_argument('--dry-run', action='store_true',
                    help='Print what would happen without copying')
    args = ap.parse_args()

    DST_DIR.mkdir(parents=True, exist_ok=True)

    src_files = sorted(SRC_DIR.glob('*.json'))
    if not src_files:
        print(f'No files in {SRC_DIR.relative_to(PROJECT_ROOT)} — nothing to merge.')
        sys.exit(0)

    copied = 0
    skipped = 0
    overwritten = 0
    for src in src_files:
        try:
            d = json.loads(src.read_text(encoding='utf-8'))
            bk = d['base_key']
        except Exception as e:
            print(f'  PARSE ERROR {src.name}: {e}')
            continue
        dst = DST_DIR / f'{bk}.json'
        exists = dst.exists()
        if exists and not args.force:
            print(f'  SKIP (exists) {bk}')
            skipped += 1
            continue
        if args.dry_run:
            print(f'  WOULD {"OVERWRITE" if exists else "COPY"} {bk}')
            continue
        shutil.copy2(src, dst)
        if exists:
            overwritten += 1
        else:
            copied += 1

    print()
    print(f'Source files: {len(src_files)}')
    if args.dry_run:
        print('Dry run — no files copied.')
    else:
        print(f'Copied (new): {copied}')
        print(f'Overwritten:  {overwritten}')
        print(f'Skipped:      {skipped}')


if __name__ == '__main__':
    main()
