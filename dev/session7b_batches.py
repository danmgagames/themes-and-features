"""
Session 7b wave-builder — classify Bucket C web_extracts.

Reads data/web_extracts/ + data/classified/, dedups against base_keys that
are already classified, emits batches of 10 to dev/_session7b_batches/.

Sub-agents will write to data/classified_7/<base_key>.json (NOT classified/).
A merge step copies into data/classified/ once validation passes.
"""

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = PROJECT_ROOT / 'data' / 'web_extracts'
CLASSIFIED_DIR = PROJECT_ROOT / 'data' / 'classified'
OUT_DIR = PROJECT_ROOT / 'dev' / '_session7b_batches'

BATCH_SIZE = 10


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

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
    for p in sorted(WEB_DIR.glob('*.json')):
        d = json.loads(p.read_text(encoding='utf-8'))
        bk = d['base_key']
        if bk in classified_base_keys:
            continue  # already enriched (Sessions 5 / 6a-c)
        candidates.append(d)

    cat_priority = {'SLOTS5': 0, 'MEGAWAYS': 1, 'BINGO': 2, 'SLOTS3': 3, 'RULETA': 4}
    candidates.sort(key=lambda d: (cat_priority.get(d.get('folder_category', ''), 9), d['base_key']))

    print(f'Target this session: {len(candidates)} base_keys')
    cat_counts: dict[str, int] = {}
    for d in candidates:
        c = d.get('folder_category') or '(none)'
        cat_counts[c] = cat_counts.get(c, 0) + 1
    for c, n in sorted(cat_counts.items()):
        print(f'  {c:<10} {n}')

    batches = [candidates[i:i + BATCH_SIZE] for i in range(0, len(candidates), BATCH_SIZE)]
    print(f'\nBatches of up to {BATCH_SIZE}: {len(batches)}')

    for bi, batch in enumerate(batches, 1):
        items = []
        for d in batch:
            text = (d.get('raw_text') or '').replace('�', '?')
            text = text[:3500]
            items.append({
                'base_key': d['base_key'],
                'folder_game_name': d.get('folder_game_name', ''),
                'folder_category': d.get('folder_category', ''),
                'market': d.get('market', ''),
                'es_commercial_name': (d.get('market_lookup') or {}).get('es_commercial_name'),
                'web_url': d.get('web_url', ''),
                'web_slug': d.get('web_slug', ''),
                'web_source_language': d.get('web_source_language', 'ES'),
                'web_fields': d.get('web_fields', {}),
                'raw_text': text,
            })
        out_path = OUT_DIR / f'batch_{bi:02d}.json'
        out_path.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding='utf-8')
        print(f'  Wrote {out_path.relative_to(PROJECT_ROOT)} - {len(items)} games')


if __name__ == '__main__':
    main()
