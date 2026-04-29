"""
Untagged-games triage — diagnostic CSV across all 6 AM markets.

Read-only. Classifies each untagged AM Masterlist row by root cause:

    A. No market_names.xlsx entry at all — generate_market_xlsx.find_base_key
       returns None (within-market + cross-market both fail).
    B. market_names match -> base_key, but no PPTX and no PDF anywhere
    C. market_names match -> base_key, and PPTX or PDF exists, but base_key
       missing from games_enriched.csv (or themes/features are blank)
    E. AM Category=EXTERNAL — out of MGA-developed scope

    (Bucket D — "cross-market resolution needed" — was retired in commit
    that added cross-market fallback to find_base_key. Cross-market matches
    are now treated identically to within-market matches.)
"""
import csv
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from agents.am_masterlist import load_am_market
from agents.extractor import _find_game_folders, _select_pptx
from agents.pdf_extractor import _build_commercial_lookup, _resolve_base_key_per_market

AM_PATH         = PROJECT_ROOT / 'config' / 'AM_Masterlist.xlsx'
MN_PATH         = PROJECT_ROOT / 'config' / 'market_names.xlsx'
ENRICHED_PATH   = PROJECT_ROOT / 'output' / 'games_enriched.csv'
PDF_SURVEY_PATH = PROJECT_ROOT / 'output' / 'pdf_coverage_survey.csv'
PPTX_ROOT       = PROJECT_ROOT / 'data' / '01_Definicion Productos'
WEB_EXTRACTS    = PROJECT_ROOT / 'data' / 'web_extracts'
OUTPUT_PATH     = PROJECT_ROOT / 'output' / 'untagged_triage.csv'

MARKETS = ['SPAIN', 'PORTUGAL', '.COM', 'NETHERLANDS', 'ITALY', 'COLOMBIA']
WITHIN_MARKET_METHODS = {'mn_exact', 'mn_fuzzy'}
CROSS_MARKET_METHODS = {'mn_exact_xmarket', 'mn_fuzzy_xmarket'}


def load_enriched() -> dict:
    by_bk = {}
    if not ENRICHED_PATH.exists():
        return by_bk
    with open(ENRICHED_PATH, 'r', encoding='utf-8-sig', newline='') as f:
        for r in csv.DictReader(f):
            bk = (r.get('base_key') or '').strip()
            if bk:
                by_bk[bk] = r
    return by_bk


def load_pdf_coverage() -> dict:
    """{base_key: (pdf_path, match_method)} — first hit per base_key."""
    cov = {}
    if not PDF_SURVEY_PATH.exists():
        return cov
    with open(PDF_SURVEY_PATH, 'r', encoding='utf-8-sig', newline='') as f:
        for r in csv.DictReader(f):
            bk = (r.get('matched_base_key') or '').strip()
            pdf_path = (r.get('pdf_path') or '').strip()
            if bk and pdf_path and bk not in cov:
                cov[bk] = (pdf_path, r.get('match_method') or '')
    return cov


def load_web_coverage() -> dict:
    """Read data/web_extracts/<base_key>.json — return {base_key: web_url}."""
    out = {}
    if not WEB_EXTRACTS.exists():
        return out
    import json
    for p in WEB_EXTRACTS.glob('*.json'):
        try:
            rec = json.loads(p.read_text(encoding='utf-8'))
        except Exception:
            continue
        bk = rec.get('base_key')
        url = rec.get('web_url') or ''
        if bk and url:
            out[bk] = url
    return out


def build_pptx_coverage(mn_exact: dict, mn_by_market: dict) -> dict:
    """Walk PPTX root, resolve each game folder to a base_key, return
    {base_key: pptx_path}. SPAIN used as default market label since the
    Definicion Productos tree is Spain-localised; cross-market fallback in
    _resolve_base_key_per_market catches the rest."""
    out = {}
    if not PPTX_ROOT.exists():
        return out
    for game in _find_game_folders(PPTX_ROOT):
        pptx = _select_pptx(game['folder_path'])
        if not pptx:
            continue
        clean = game['folder_game_name'].replace('_', ' ').strip()
        bk, _, _ = _resolve_base_key_per_market(clean, 'SPAIN', mn_exact, mn_by_market)
        if bk and bk not in out:
            out[bk] = pptx
    return out


def is_external(category) -> bool:
    return str(category or '').strip().upper() == 'EXTERNAL'


def classify_row(am_row, market, mn_exact, mn_by_market, enriched, pdf_cov, pptx_cov, web_cov):
    game_name = str(am_row.get('GameName') or '').strip()
    category = str(am_row.get('Category') or '').strip()

    if is_external(category):
        return None, {'bucket': 'E', 'notes': 'AM Category=EXTERNAL'}

    bk, _conf, method = _resolve_base_key_per_market(
        game_name, market, mn_exact, mn_by_market,
    )

    enr = enriched.get(bk) if bk else None
    has_themes = bool(enr and (enr.get('themes') or '').strip())
    has_features = bool(enr and (enr.get('features') or '').strip())
    has_tags = has_themes or has_features

    pptx_path = pptx_cov.get(bk, '') if bk else ''
    pdf_path, pdf_method = pdf_cov.get(bk, ('', '')) if bk else ('', '')
    web_url = web_cov.get(bk, '') if bk else ''
    has_pptx = bool(pptx_path)
    has_pdf = bool(pdf_path)
    has_web = bool(web_url)

    common = {
        'base_key': bk or '',
        'mn_method': method,
        'has_pptx': has_pptx,
        'pptx_path': str(pptx_path),
        'has_pdf': has_pdf,
        'pdf_path': pdf_path,
        'pdf_method': pdf_method,
        'has_web': has_web,
        'web_url': web_url,
        'in_enriched': bool(enr),
        'has_themes': has_themes,
        'has_features': has_features,
    }

    if method == 'none':
        return common, {'bucket': 'A', 'notes': 'no market_names.xlsx entry'}

    # find_base_key now does cross-market fallback, so within-market and
    # cross-market matches are equivalent for bucket purposes.
    if has_tags:
        return common, {'bucket': '_TAGGED', 'notes': ''}

    src_parts = []
    if has_pptx:
        src_parts.append('PPTX')
    if has_pdf:
        src_parts.append('PDF')
    if has_web:
        src_parts.append('WEB')

    method_note = f' (matched via {method})' if method in CROSS_MARKET_METHODS else ''
    if not src_parts:
        return common, {'bucket': 'B', 'notes': f'no PPTX, no PDF{method_note}'}

    return common, {
        'bucket': 'C',
        'notes': f"source exists ({'+'.join(src_parts)}); base_key not in enriched "
                 f"or themes/features blank{method_note}"
    }


def _fmt_release_date(rd) -> str:
    if rd is None:
        return ''
    if isinstance(rd, datetime):
        return rd.date().isoformat()
    return str(rd)


def main():
    if not AM_PATH.exists():
        sys.exit(f"AM_Masterlist not found: {AM_PATH}")
    if not MN_PATH.exists():
        sys.exit(f"market_names.xlsx not found: {MN_PATH}")

    print('Loading market_names per-market lookup...')
    mn_exact, mn_by_market = _build_commercial_lookup(MN_PATH)
    print(f'  {len(mn_exact)} (market, name) entries')

    print(f'Loading {ENRICHED_PATH.name}...')
    enriched = load_enriched()
    print(f'  {len(enriched)} enriched base_keys')

    print(f'Loading {PDF_SURVEY_PATH.name}...')
    pdf_cov = load_pdf_coverage()
    print(f'  {len(pdf_cov)} base_keys with PDF coverage')

    print(f'Walking PPTX root: {PPTX_ROOT}')
    pptx_cov = build_pptx_coverage(mn_exact, mn_by_market)
    print(f'  {len(pptx_cov)} base_keys with PPTX coverage')

    print(f'Loading {WEB_EXTRACTS.name}/...')
    web_cov = load_web_coverage()
    print(f'  {len(web_cov)} base_keys with WEB coverage')

    out_rows = []
    summary = Counter()       # (market, bucket) -> count
    market_totals = Counter() # market -> emitted (untagged) count
    seen = Counter()          # market -> all AM rows seen

    for market in MARKETS:
        am_rows = load_am_market(AM_PATH, market)
        for row in am_rows:
            seen[market] += 1
            common, verdict = classify_row(row, market, mn_exact, mn_by_market,
                                           enriched, pdf_cov, pptx_cov, web_cov)
            bucket = verdict['bucket']
            if bucket == '_TAGGED':
                continue

            row_out = {
                'market': market,
                'game_name': str(row.get('GameName') or '').strip(),
                'category': str(row.get('Category') or '').strip(),
                'tier': str(row.get('TIER') or '').strip(),
                'release_date': _fmt_release_date(row.get('Release Date')),
                'matched_base_key': '',
                'market_names_match_method': '',
                'has_pptx': False,
                'pptx_path': '',
                'has_pdf': False,
                'pdf_path': '',
                'pdf_match_method': '',
                'has_web': False,
                'web_url': '',
                'base_key_in_enriched': False,
                'has_themes': False,
                'has_features': False,
                'root_cause_bucket': bucket,
                'notes': verdict.get('notes', ''),
            }
            if common is not None:
                row_out.update({
                    'matched_base_key': common['base_key'],
                    'market_names_match_method': common['mn_method'],
                    'has_pptx': common['has_pptx'],
                    'pptx_path': common['pptx_path'],
                    'has_pdf': common['has_pdf'],
                    'pdf_path': common['pdf_path'],
                    'pdf_match_method': common['pdf_method'],
                    'has_web': common['has_web'],
                    'web_url': common['web_url'],
                    'base_key_in_enriched': common['in_enriched'],
                    'has_themes': common['has_themes'],
                    'has_features': common['has_features'],
                })
            out_rows.append(row_out)
            summary[(market, bucket)] += 1
            market_totals[market] += 1

    cols = [
        'market', 'game_name', 'category', 'tier', 'release_date',
        'matched_base_key', 'market_names_match_method',
        'has_pptx', 'pptx_path', 'has_pdf', 'pdf_path', 'pdf_match_method',
        'has_web', 'web_url',
        'base_key_in_enriched', 'has_themes', 'has_features',
        'root_cause_bucket', 'notes',
    ]
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in sorted(out_rows,
                        key=lambda x: (x['root_cause_bucket'],
                                       MARKETS.index(x['market']),
                                       x['game_name'].lower())):
            w.writerow(r)

    print()
    print(f'Wrote {OUTPUT_PATH.relative_to(PROJECT_ROOT)} ({len(out_rows)} rows)')
    print()

    market_w = max(len('Bucket'), *(len(m) for m in MARKETS))
    header = f"{'Bucket':<8}{'Total':>7}  " + ' '.join(f'{m:>{market_w}}' for m in MARKETS)
    print(header)
    print('-' * len(header))
    for bucket in ['A', 'B', 'C', 'E']:
        per_market = [summary[(m, bucket)] for m in MARKETS]
        total = sum(per_market)
        print(f"{bucket:<8}{total:>7}  " + ' '.join(f'{n:>{market_w}}' for n in per_market))

    print('-' * len(header))
    grand = sum(market_totals.values())
    per_market = [market_totals[m] for m in MARKETS]
    print(f"{'TOTAL':<8}{grand:>7}  " + ' '.join(f'{n:>{market_w}}' for n in per_market))
    print()
    seen_per = [seen[m] for m in MARKETS]
    print(f"{'AM rows':<8}{sum(seen_per):>7}  "
          + ' '.join(f'{n:>{market_w}}' for n in seen_per))
    pct = [(market_totals[m] / seen[m] * 100) if seen[m] else 0 for m in MARKETS]
    print(f"{'% blank':<8}{(grand/sum(seen_per)*100 if sum(seen_per) else 0):>6.1f}%  "
          + ' '.join(f'{p:>{market_w-1}.1f}%' for p in pct))

    print()
    print('Bucket key:')
    print('  A  no market_names.xlsx entry (xlsx find_base_key returns None)')
    print('  B  base_key resolves; no PPTX, PDF, or WEB — genuine source absence')
    print('  C  base_key resolves; PPTX/PDF/WEB exists; base_key missing/blank in enriched')
    print('  E  AM Category=EXTERNAL — out of MGA-developed scope')


if __name__ == '__main__':
    main()
