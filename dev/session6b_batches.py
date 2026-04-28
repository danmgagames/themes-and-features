"""
Session 6b wave-builder — same as 6a but pulls all remaining NEW base_keys.

Reads data/pdf_extracts/ + output/games_enriched.csv + data/classified/,
emits batches of 8 to dev/_session6b_batches/.
"""

import csv
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PDF_DIR = PROJECT_ROOT / 'data' / 'pdf_extracts'
ENRICHED = PROJECT_ROOT / 'output' / 'games_enriched.csv'
CLASSIFIED_DIR = PROJECT_ROOT / 'data' / 'classified'
OUT_DIR = PROJECT_ROOT / 'dev' / '_session6b_batches'

BATCH_SIZE = 8


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    enriched_keys: set[str] = set()
    if ENRICHED.exists():
        with open(ENRICHED, 'r', encoding='utf-8-sig') as f:
            for r in csv.DictReader(f):
                if (r.get('themes', '').strip() or r.get('features', '').strip()):
                    enriched_keys.add(r['base_key'].strip())

    # Already-classified base_keys (from 6a + Session 5 backfills will live here in 6c)
    # Match by reading actual base_key from JSON content (filename can differ from base_key).
    classified_base_keys: set[str] = set()
    for p in CLASSIFIED_DIR.glob('*.json'):
        try:
            d = json.loads(p.read_text(encoding='utf-8'))
            bk = d.get('base_key')
            if bk:
                classified_base_keys.add(bk)
        except Exception:
            pass

    candidates = []
    for p in sorted(PDF_DIR.glob('*.json')):
        d = json.loads(p.read_text(encoding='utf-8'))
        bk = d['base_key']
        if bk in enriched_keys:
            continue  # backfill — defer to 6c
        if bk in classified_base_keys:
            continue  # 6a already did this
        candidates.append(d)

    cat_priority = {'SLOTS5': 0, 'MEGAWAYS': 1, 'BINGO': 2, 'SLOTS3': 3, 'RULETA': 4}
    candidates.sort(key=lambda d: (cat_priority.get(d['folder_category'], 9), d['base_key']))

    print(f'Target this session: {len(candidates)} base_keys')
    cat_counts: dict[str, int] = {}
    for d in candidates:
        cat_counts[d['folder_category']] = cat_counts.get(d['folder_category'], 0) + 1
    for c, n in sorted(cat_counts.items()):
        print(f'  {c:<10} {n}')

    batches = [candidates[i:i + BATCH_SIZE] for i in range(0, len(candidates), BATCH_SIZE)]
    print(f'\nBatches of up to {BATCH_SIZE}: {len(batches)}')

    for bi, batch in enumerate(batches, 1):
        items = []
        for d in batch:
            text = d['raw_text'].replace('�', '?')
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
