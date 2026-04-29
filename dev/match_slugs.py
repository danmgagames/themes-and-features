"""
Match scraped mga.games slugs to base_keys.

Reads:
  dev/_scrape/catalog.csv     (market, slug, displayed_name, category)
  dev/_scrape/games.csv       (slug, description, ...)
  config/market_names.xlsx    (per-market commercial-name lookup)
  output/games_enriched.csv   (existing enrichment)
  output/untagged_triage.csv  (current untagged rows)

Writes:
  dev/_scrape/slug_to_base_key.csv   per-tile resolution + match method
  dev/_scrape/scrape_coverage.csv    summary: which Bucket A/B rows the
                                     scrape can fill
"""
import csv
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from agents.pdf_extractor import _build_commercial_lookup, _resolve_base_key_per_market

SCRAPE_DIR    = PROJECT_ROOT / 'dev' / '_scrape'
CATALOG_PATH  = SCRAPE_DIR / 'catalog.csv'
GAMES_PATH    = SCRAPE_DIR / 'games.csv'
MN_PATH       = PROJECT_ROOT / 'config' / 'market_names.xlsx'
ENRICHED_PATH = PROJECT_ROOT / 'output' / 'games_enriched.csv'
TRIAGE_PATH   = PROJECT_ROOT / 'output' / 'untagged_triage.csv'

OUT_SLUG_BK   = SCRAPE_DIR / 'slug_to_base_key.csv'
OUT_COVERAGE  = SCRAPE_DIR / 'scrape_coverage.csv'


def load_csv(path):
    if not path.exists():
        return []
    with open(path, 'r', encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def main():
    if not CATALOG_PATH.exists():
        sys.exit(f'No catalog: {CATALOG_PATH} — run scrape_mga.py first')

    catalog = load_csv(CATALOG_PATH)
    games   = {g['slug']: g for g in load_csv(GAMES_PATH)}
    enriched = {r['base_key']: r for r in load_csv(ENRICHED_PATH) if r.get('base_key')}
    triage = load_csv(TRIAGE_PATH)

    print(f'catalog rows: {len(catalog)} ({len({c["slug"] for c in catalog})} unique slugs)')
    print(f'games rows: {len(games)}')
    print(f'enriched: {len(enriched)} base_keys')
    print(f'triage rows: {len(triage)} untagged')

    print('\nLoading market_names per-market lookup...')
    mn_exact, mn_by_market = _build_commercial_lookup(MN_PATH)

    # Triage index: (market, normalized game_name) → bucket
    from agents.pdf_extractor import _norm
    triage_idx: dict[tuple[str, str], dict] = {}
    for t in triage:
        key = (t['market'].upper(), _norm(t['game_name']))
        triage_idx[key] = t

    out_rows = []
    for c in catalog:
        market = c['market'].upper()
        slug = c['slug']
        gdata = games.get(slug, {}) or {}
        # Prefer the per-game page title ("MGA Games - <name>") which is
        # the cleanest display name. Fall back to slug→spaces.
        title = gdata.get('title', '') or ''
        if title.lower().startswith('mga games'):
            # Strip "MGA Games - " or "MGA Games – " prefix
            for sep in (' - ', ' – ', ' — '):
                if sep in title:
                    title = title.split(sep, 1)[1]
                    break
        displayed = (c.get('displayed_name') or '').strip() or title.strip()
        if not displayed:
            displayed = slug.replace('_', ' ').replace('-', ' ')
        bk, conf, method = _resolve_base_key_per_market(
            displayed, market, mn_exact, mn_by_market,
        )
        # If the per-market match failed, try the slug-derived form as a
        # second key — slugs sometimes drop accents/punctuation that the
        # title preserves.
        if not bk:
            slug_form = slug.replace('_', ' ').replace('-', ' ')
            bk, conf, method = _resolve_base_key_per_market(
                slug_form, market, mn_exact, mn_by_market,
            )

        gdesc = gdata.get('description', '') or ''
        gtipo = gdata.get('tipo', '') or ''
        gvol = gdata.get('volatilidad', '') or ''

        in_enriched = bool(bk and bk in enriched)
        triage_hit = triage_idx.get((market, _norm(displayed)))

        out_rows.append({
            'market': market,
            'slug': slug,
            'displayed_name': displayed,
            'category': c.get('category', ''),
            'matched_base_key': bk or '',
            'mn_match_method': method,
            'mn_match_confidence': f'{conf:.2f}' if conf else '',
            'in_enriched': in_enriched,
            'enriched_has_themes': bool(in_enriched and (enriched[bk].get('themes') or '').strip()),
            'enriched_has_features': bool(in_enriched and (enriched[bk].get('features') or '').strip()),
            'has_scraped_description': bool(gdesc.strip()),
            'description_chars': len(gdesc),
            'tipo': gtipo,
            'volatilidad': gvol,
            'triage_bucket': (triage_hit or {}).get('root_cause_bucket', ''),
        })

    cols = ['market', 'slug', 'displayed_name', 'category', 'matched_base_key',
            'mn_match_method', 'mn_match_confidence',
            'in_enriched', 'enriched_has_themes', 'enriched_has_features',
            'has_scraped_description', 'description_chars',
            'tipo', 'volatilidad', 'triage_bucket']
    with open(OUT_SLUG_BK, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(out_rows)
    print(f'\nWrote {OUT_SLUG_BK.relative_to(PROJECT_ROOT)} ({len(out_rows)} rows)')

    # Coverage summary: how many triage rows can the scrape fill?
    # Triage rows have a matched_base_key column too (resolved by the same
    # _resolve_base_key_per_market). So join on (market, base_key) — way more
    # robust than fuzzy-matching display names twice.
    triage_by_bk: dict[tuple[str, str], dict] = {}
    for t in triage:
        bk_t = (t.get('matched_base_key') or '').strip()
        if bk_t:
            triage_by_bk[(t['market'].upper(), bk_t)] = t

    by_market_bucket = {}
    fillable = []
    for r in out_rows:
        if not r['matched_base_key']:
            continue
        if not r['has_scraped_description']:
            continue
        t = triage_by_bk.get((r['market'], r['matched_base_key']))
        if not t:
            continue
        bucket = t['root_cause_bucket']
        by_market_bucket.setdefault((r['market'], bucket), 0)
        by_market_bucket[(r['market'], bucket)] += 1
        fillable.append({
            'market': r['market'],
            'game_name': t['game_name'],
            'matched_base_key': r['matched_base_key'],
            'slug': r['slug'],
            'triage_bucket': bucket,
            'description_chars': r['description_chars'],
        })

    with open(OUT_COVERAGE, 'w', encoding='utf-8-sig', newline='') as f:
        ccols = ['market', 'game_name', 'matched_base_key', 'slug',
                 'triage_bucket', 'description_chars']
        w = csv.DictWriter(f, fieldnames=ccols)
        w.writeheader()
        w.writerows(sorted(fillable, key=lambda r: (r['triage_bucket'], r['market'], r['game_name'])))
    print(f'Wrote {OUT_COVERAGE.relative_to(PROJECT_ROOT)} ({len(fillable)} fillable triage rows)')

    print()
    print('Triage rows fillable by scrape (with description, base_key resolved):')
    print(f"  {'Market':<14} {'A':>4} {'B':>4} {'C':>4}  {'Total':>6}")
    markets = ['SPAIN', 'PORTUGAL', '.COM', 'NETHERLANDS', 'ITALY', 'COLOMBIA']
    for m in markets:
        a = by_market_bucket.get((m, 'A'), 0)
        b = by_market_bucket.get((m, 'B'), 0)
        c = by_market_bucket.get((m, 'C'), 0)
        print(f'  {m:<14} {a:>4} {b:>4} {c:>4}  {a+b+c:>6}')
    grand = sum(by_market_bucket.values())
    print(f'  {"TOTAL":<14} {"":<14}  {grand:>6}')


if __name__ == '__main__':
    main()
