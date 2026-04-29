"""
Convert scraped mga.games per-game records into web_extract JSON files,
parallel in shape to data/pdf_extracts/<base_key>.json.

For each unique base_key in the scrape, picks the best (market, slug) tuple
(SPAIN preferred, then by match_method preference: mn_exact > mn_fuzzy >
xmarket variants) and writes a JSON to data/web_extracts/<base_key>.json.

raw_text combines the description + tipo / volatilidad / apuesta / premio_max
fields so the classifier sub-agents have all on-page facts in one block.
"""
import csv
import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from agents.localisation_resolver import build_game_families, load_market_db

SCRAPE = PROJECT_ROOT / 'dev' / '_scrape'
OUT_DIR = PROJECT_ROOT / 'data' / 'web_extracts'
OUT_DIR.mkdir(parents=True, exist_ok=True)
MN_PATH = PROJECT_ROOT / 'config' / 'market_names.xlsx'

METHOD_RANK = {
    'mn_exact': 0, 'mn_fuzzy': 1,
    'mn_exact_xmarket': 2, 'mn_fuzzy_xmarket': 3, 'none': 9,
}
MARKET_RANK = {
    'SPAIN': 0, 'PORTUGAL': 1, '.COM': 2,
    'ITALY': 3, 'NETHERLANDS': 4, 'COLOMBIA': 5,
}


def safe_filename(s):
    return re.sub(r'[^\w\-]', '_', s)


def main():
    slug_bk_rows = []
    with open(SCRAPE / 'slug_to_base_key.csv', 'r', encoding='utf-8-sig', newline='') as f:
        slug_bk_rows = list(csv.DictReader(f))

    games = {}
    with open(SCRAPE / 'games.csv', 'r', encoding='utf-8-sig', newline='') as f:
        for r in csv.DictReader(f):
            games[r['slug']] = r

    print(f'Loading families from {MN_PATH.name}...')
    market_rows = load_market_db(MN_PATH)
    families = build_game_families(market_rows)

    # Group resolutions by base_key — pick best per base_key
    by_bk: dict[str, list[dict]] = {}
    for r in slug_bk_rows:
        bk = (r.get('matched_base_key') or '').strip()
        if not bk:
            continue
        if not games.get(r['slug'], {}).get('description', '').strip():
            continue
        by_bk.setdefault(bk, []).append(r)

    written = 0
    skipped = 0
    for bk, candidates in by_bk.items():
        # Pick the best candidate: prefer mn_exact over fuzzy/xmarket, then SPAIN
        candidates.sort(key=lambda c: (
            METHOD_RANK.get(c['mn_match_method'], 9),
            MARKET_RANK.get(c['market'], 9),
        ))
        best = candidates[0]
        slug = best['slug']
        gdata = games.get(slug, {})

        # Compose raw_text — description plus a structured RESUMEN block.
        parts = []
        desc = (gdata.get('description') or '').strip()
        if desc:
            parts.append(desc)
        resumen = []
        for label, key in [('Tipo de juego', 'tipo'), ('Apuesta', 'apuesta'),
                           ('Volatilidad', 'volatilidad'), ('Premio máximo', 'premio_max')]:
            v = (gdata.get(key) or '').strip()
            if v:
                resumen.append(f'{label}: {v}')
        if resumen:
            parts.append('RESUMEN\n' + '\n'.join(resumen))
        raw_text = '\n\n'.join(parts).strip()

        fam = families.get(bk, {})
        record = {
            'base_key': bk,
            'folder_game_name': '',
            'folder_category': fam.get('category') or '',
            'market': best['market'],
            'market_label': best['market'],
            'web_url': gdata.get('url') or f"https://mga.games/games/{slug}",
            'web_slug': slug,
            'web_found': True,
            'web_source_language': 'ES',  # Description is Spanish
            'raw_text': raw_text,
            'raw_text_chars': len(raw_text),
            'web_fields': {
                'title': gdata.get('title') or '',
                'tipo': gdata.get('tipo') or '',
                'apuesta': gdata.get('apuesta') or '',
                'volatilidad': gdata.get('volatilidad') or '',
                'premio_max': gdata.get('premio_max') or '',
            },
            'all_market_slugs': [
                {'market': c['market'], 'slug': c['slug'],
                 'method': c['mn_match_method'],
                 'confidence': c.get('mn_match_confidence', '')}
                for c in candidates
            ],
            'market_lookup': {
                'base_key': bk,
                'es_commercial_name': fam.get('es_commercial_name'),
                'category': fam.get('category'),
                'markets': fam.get('markets', []),
                'celebrity_names': fam.get('celebrity_names', []),
                'match_confidence': float(best.get('mn_match_confidence') or 0),
                'match_method': best['mn_match_method'],
            },
        }

        out_path = OUT_DIR / f'{safe_filename(bk)}.json'
        out_path.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding='utf-8')
        written += 1

    print(f'Wrote {written} web_extract JSONs to {OUT_DIR.relative_to(PROJECT_ROOT)}/')
    print(f'Skipped {skipped} candidates without descriptions')

    # Coverage summary for triage rows
    triage_path = PROJECT_ROOT / 'output' / 'untagged_triage.csv'
    triage = list(csv.DictReader(open(triage_path, encoding='utf-8-sig')))
    triage_bks = {(t['market'], t['matched_base_key']): t for t in triage if t.get('matched_base_key')}
    web_bks = set(by_bk.keys())
    fillable = [t for (m, bk), t in triage_bks.items() if bk in web_bks]
    bucket_counts = {}
    for t in fillable:
        bucket_counts[t['root_cause_bucket']] = bucket_counts.get(t['root_cause_bucket'], 0) + 1
    print()
    print(f'Triage rows now reachable via data/web_extracts/: {len(fillable)}')
    for b in ['A', 'B', 'C']:
        print(f'  Bucket {b}: {bucket_counts.get(b, 0)}')


if __name__ == '__main__':
    main()
