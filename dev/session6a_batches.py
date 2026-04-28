"""
Session 6a wave-builder.

Reads data/pdf_extracts/ + output/games_enriched.csv, computes the 6a target
set (NEW base_keys not yet classified), splits into batches of 8, and emits
one JSON file per batch under dev/_session6a_batches/.

Each batch JSON is the array of game-input dicts ready to be inlined into a
sub-agent prompt.
"""

import csv
import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PDF_DIR = PROJECT_ROOT / 'data' / 'pdf_extracts'
ENRICHED = PROJECT_ROOT / 'output' / 'games_enriched.csv'
CLASSIFIED_DIR = PROJECT_ROOT / 'data' / 'classified'
OUT_DIR = PROJECT_ROOT / 'dev' / '_session6a_batches'

# Mojibake cleanup hints (best-guess Spanish characters). Sub-agent does the
# real work; we just pre-clean the text we hand off so it sees fewer artefacts.
MOJIBAKE_MAP = {
    '�': '?',  # placeholder
}

BATCH_SIZE = 8
TARGET_TOTAL = 80   # 6a quota — 6b will pick up the rest


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Already-enriched (Session 5) base_keys — skip
    enriched_keys: set[str] = set()
    if ENRICHED.exists():
        with open(ENRICHED, 'r', encoding='utf-8-sig') as f:
            for r in csv.DictReader(f):
                if (r.get('themes', '').strip() or r.get('features', '').strip()):
                    enriched_keys.add(r['base_key'].strip())

    # Already-classified-this-session (calibration JSONs)
    classified_now = {p.stem for p in CLASSIFIED_DIR.glob('*.json')}

    # All PDF extracts
    candidates = []
    for p in sorted(PDF_DIR.glob('*.json')):
        d = json.loads(p.read_text(encoding='utf-8'))
        bk = d['base_key']
        if bk in enriched_keys:
            continue  # backfill — defer to 6c
        if bk in classified_now and (CLASSIFIED_DIR / f'{bk}.json').exists():
            # Skip if already classified in this session (e.g. calibration output)
            if (CLASSIFIED_DIR / f'{bk}.json').stat().st_size > 0:
                continue
        candidates.append(d)

    # Target the first TARGET_TOTAL — bias toward SLOTS5/MEGAWAYS first
    # (richer PDFs, and they cover the SPAIN/PORTUGAL/COLOMBIA SPAIN-AM rows)
    cat_priority = {'SLOTS5': 0, 'MEGAWAYS': 1, 'BINGO': 2, 'SLOTS3': 3, 'RULETA': 4}
    candidates.sort(key=lambda d: (cat_priority.get(d['folder_category'], 9), d['base_key']))
    target = candidates[:TARGET_TOTAL]

    print(f'Target this session: {len(target)} base_keys')
    cat_counts: dict[str, int] = {}
    for d in target:
        cat_counts[d['folder_category']] = cat_counts.get(d['folder_category'], 0) + 1
    for c, n in sorted(cat_counts.items()):
        print(f'  {c:<10} {n}')

    # Build batches
    batches = [target[i:i + BATCH_SIZE] for i in range(0, len(target), BATCH_SIZE)]
    print(f'\nBatches of {BATCH_SIZE}: {len(batches)}')

    for bi, batch in enumerate(batches, 1):
        items = []
        for d in batch:
            text = d['raw_text']
            for k, v in MOJIBAKE_MAP.items():
                text = text.replace(k, v)
            # Trim to ~3000 chars to keep prompts compact (PDFs rarely exceed 2.5k)
            text = text[:3500]
            items.append({
                'base_key': d['base_key'],
                'folder_game_name': d['folder_game_name'],
                'folder_category': d['folder_category'],
                'market': d['market'],
                'es_commercial_name': d['market_lookup'].get('es_commercial_name'),
                'pdf_source_language': d['pdf_source_language'],
                'raw_text': text,
            })
        out_path = OUT_DIR / f'batch_{bi:02d}.json'
        out_path.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding='utf-8')
        print(f'  Wrote {out_path.relative_to(PROJECT_ROOT)} — {len(items)} games')


if __name__ == '__main__':
    main()
