"""
Generate output/themes_features_by_market.xlsx — one sheet per market with
columns: GameName, Category, Themes, Features, Description.

Joins:
  AM_Masterlist (market sheets, localised names) →
  market_names.xlsx (commercial name → tablename → base_key) →
  output/games_enriched.csv (themes, features, description by base_key)
"""

import csv
import re
import unicodedata
from pathlib import Path

import openpyxl
from openpyxl.styles import Font, PatternFill
from rapidfuzz import fuzz, process

PROJECT_ROOT = Path(__file__).resolve().parent
AM_PATH = PROJECT_ROOT / 'config' / 'AM_Masterlist.xlsx'
MN_PATH = PROJECT_ROOT / 'config' / 'market_names.xlsx'
ENRICHED_PATH = PROJECT_ROOT / 'output' / 'games_enriched.csv'
OUTPUT_PATH = PROJECT_ROOT / 'output' / 'themes_features_by_market.xlsx'

SUFFIX_PATTERN = re.compile(r'(NoIp|Es|Pt|It|Co|Nl|Ca|Se)$', re.IGNORECASE)
FUZZY_THRESHOLD = 88


def norm(s) -> str:
    if s is None:
        return ''
    s = str(s).strip().lower()
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode('ascii')
    return ' '.join(s.split())


def load_mn_lookup() -> dict:
    """Build lookup: (market_upper, normalized_commercial_name) → base_key."""
    wb = openpyxl.load_workbook(str(MN_PATH), read_only=True)
    ws = wb.active
    headers = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]

    lookup = {}
    by_market_norms = {}

    for raw in ws.iter_rows(min_row=2, values_only=True):
        d = dict(zip(headers, raw))
        market = str(d.get('MARKET') or '').upper().strip()
        cname = str(d.get('COMMERCIAL NAME') or '').strip()
        tablename = str(d.get('tablename') or '').strip()
        if not (market and cname and tablename):
            continue
        base_key = SUFFIX_PATTERN.sub('', tablename)
        n = norm(cname)
        lookup[(market, n)] = base_key
        by_market_norms.setdefault(market, []).append((n, base_key))

    wb.close()
    return lookup, by_market_norms


def load_enriched() -> dict:
    """Load enriched CSV, return dict by base_key."""
    by_base = {}
    if not ENRICHED_PATH.exists():
        return by_base
    with open(ENRICHED_PATH, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for r in reader:
            bk = r.get('base_key', '').strip()
            if bk:
                by_base[bk] = r
    return by_base


def find_base_key(am_name: str, market: str, mn_lookup: dict, mn_market_norms: dict) -> str | None:
    """Match AM GameName → mn base_key for the given market."""
    n = norm(am_name)
    if not n:
        return None
    bk = mn_lookup.get((market.upper(), n))
    if bk:
        return bk

    candidates = mn_market_norms.get(market.upper(), [])
    if not candidates:
        return None
    norms_list = [c[0] for c in candidates]
    res = process.extractOne(n, norms_list, scorer=fuzz.token_sort_ratio)
    if res and res[1] >= FUZZY_THRESHOLD:
        return candidates[res[2]][1]
    return None


def main():
    if not AM_PATH.exists():
        raise SystemExit(f"AM_Masterlist not found: {AM_PATH}")
    if not ENRICHED_PATH.exists():
        raise SystemExit(f"Enriched CSV not found: {ENRICHED_PATH}. Run consolidate first.")

    mn_lookup, mn_market_norms = load_mn_lookup()
    enriched = load_enriched()
    print(f"Loaded {len(enriched)} enriched games, {len(mn_lookup)} mn (market, name) lookups")

    am_wb = openpyxl.load_workbook(str(AM_PATH), read_only=True, data_only=True)
    out_wb = openpyxl.Workbook()
    out_wb.remove(out_wb.active)

    header_font = Font(bold=True, color='FFFFFF')
    header_fill = PatternFill('solid', fgColor='2F4F4F')

    summary = []

    for sheet_name in am_wb.sheetnames:
        am_ws = am_wb[sheet_name]
        rows_iter = am_ws.iter_rows(values_only=True)
        am_headers = next(rows_iter, None)
        if not am_headers:
            continue

        out_ws = out_wb.create_sheet(title=sheet_name[:31])
        out_ws.append(['GameName', 'Category', 'Themes', 'Features', 'Description'])
        for cell in out_ws[1]:
            cell.font = header_font
            cell.fill = header_fill

        market_key = sheet_name.upper().strip()
        n_total = 0
        n_matched = 0

        for raw in rows_iter:
            if not raw:
                continue
            game_name = raw[0]
            if not game_name:
                continue
            n_total += 1
            category = raw[1] if len(raw) > 1 else ''

            bk = find_base_key(str(game_name), market_key, mn_lookup, mn_market_norms)
            themes = ''
            features = ''
            description = ''
            if bk and bk in enriched:
                themes = enriched[bk].get('themes', '')
                features = enriched[bk].get('features', '')
                description = enriched[bk].get('description', '')
                n_matched += 1

            out_ws.append([
                str(game_name).strip(),
                str(category or ''),
                themes,
                features,
                description,
            ])

        out_ws.column_dimensions['A'].width = 40
        out_ws.column_dimensions['B'].width = 14
        out_ws.column_dimensions['C'].width = 50
        out_ws.column_dimensions['D'].width = 60
        out_ws.column_dimensions['E'].width = 80
        out_ws.freeze_panes = 'A2'

        summary.append((sheet_name, n_total, n_matched))

    am_wb.close()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    target = OUTPUT_PATH
    try:
        out_wb.save(str(target))
    except PermissionError:
        # File likely open in Excel — write to a sibling path so the run still
        # produces an artefact the user can compare against.
        target = OUTPUT_PATH.with_name(OUTPUT_PATH.stem + '.LATEST.xlsx')
        out_wb.save(str(target))
        print()
        print(f'NOTE: Could not overwrite {OUTPUT_PATH.name} (likely open in Excel).')
        print(f'      Wrote to {target.name} instead — close Excel and rename.')

    print()
    print(f"Wrote {OUTPUT_PATH}")
    print(f"{'Market':<14} {'Rows':>6} {'Enriched':>9} {'Coverage':>9}")
    for name, total, matched in summary:
        pct = (matched / total * 100) if total else 0
        print(f"{name:<14} {total:>6} {matched:>9} {pct:>8.1f}%")


if __name__ == '__main__':
    main()
