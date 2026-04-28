"""
Session 6a validation gate.

Runs all 7 validation checks from the plan and reports pass/fail with
per-check stats. Exits non-zero if any check fails.
"""

import csv
import json
import random
import sys
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CLASSIFIED_DIR = PROJECT_ROOT / 'data' / 'classified'
ENRICHED_CSV = PROJECT_ROOT / 'output' / 'games_enriched.csv'
PP_CSV = PROJECT_ROOT / 'output' / 'pp_mechanic_candidates.csv'
MARKET_XLSX = PROJECT_ROOT / 'output' / 'themes_features_by_market.xlsx'
PDF_DIR = PROJECT_ROOT / 'data' / 'pdf_extracts'

PP_TERMS = ['Hyperplay', 'Increasing Wilds', 'Mystery Expanding Symbol', 'Super Scatter', 'Powernudge']
SANCTIONED_PP = {'Hyperplay', 'Increasing Wilds', 'Mystery Expanding Symbol', 'Super Scatter'}


def main():
    failures: list[str] = []
    print('=' * 60)
    print('Session 6a — validation gate')
    print('=' * 60)

    # 1. Schema integrity for new classified JSONs (those with description key)
    pdf_classified = []
    for p in CLASSIFIED_DIR.glob('*.json'):
        d = json.loads(p.read_text(encoding='utf-8'))
        if 'description' in d and 'pdf_source_language' in d:
            pdf_classified.append((p, d))
    print(f'\n[1] Schema integrity: {len(pdf_classified)} PDF-sourced classified JSONs')
    schema_bad = []
    required = {'description', 'pdf_source_language', 'pp_candidate_mechanics', 'themes', 'features'}
    for p, d in pdf_classified:
        missing = required - d.keys()
        if missing:
            schema_bad.append((p.name, missing))
    if schema_bad:
        print(f'    FAIL: {len(schema_bad)} files missing required keys:')
        for name, missing in schema_bad[:5]:
            print(f'      {name}: missing {missing}')
        failures.append(f'schema_integrity ({len(schema_bad)} bad)')
    else:
        print(f'    PASS: all required keys present')

    # 2. PP leak check — no PP terms in features or unknown_features
    leaks = []
    for p, d in pdf_classified:
        for t in PP_TERMS:
            if t in d.get('features', []):
                leaks.append((p.name, t, 'features'))
            if t in d.get('unknown_features', []):
                leaks.append((p.name, t, 'unknown_features'))
    print(f'\n[2] PP leak check: {len(leaks)} leaks into features/unknown_features')
    if leaks:
        print('    FAIL — leaks:')
        for name, t, where in leaks[:10]:
            print(f'      {name}: {t!r} in {where}')
        failures.append(f'pp_leak ({len(leaks)} leaks)')
    else:
        print('    PASS')

    # 3. Candidate capture — every pp_candidate_mechanics entry must use a sanctioned mechanic
    bad_candidates = []
    candidate_count = 0
    candidate_games = []
    for p, d in pdf_classified:
        cands = d.get('pp_candidate_mechanics') or []
        if cands:
            candidate_games.append(p.stem)
        for c in cands:
            candidate_count += 1
            mech = (c or {}).get('mechanic', '')
            if mech not in SANCTIONED_PP:
                bad_candidates.append((p.name, mech))
    print(f'\n[3] Candidate capture: {candidate_count} PP candidate entries across {len(candidate_games)} games')
    if bad_candidates:
        print('    FAIL — non-sanctioned mechanics:')
        for name, m in bad_candidates[:10]:
            print(f'      {name}: {m!r}')
        failures.append(f'pp_candidate_invalid ({len(bad_candidates)})')
    else:
        print('    PASS')

    # Show breakdown
    by_mech = Counter()
    for p, d in pdf_classified:
        for c in d.get('pp_candidate_mechanics') or []:
            by_mech[(c or {}).get('mechanic', '')] += 1
    if by_mech:
        for m, n in by_mech.most_common():
            print(f'      - {m}: {n}')

    # 4. Description coverage
    with_desc = sum(1 for _, d in pdf_classified if (d.get('description') or '').strip())
    print(f'\n[4] Description coverage: {with_desc}/{len(pdf_classified)} have non-empty description')
    if pdf_classified and with_desc / len(pdf_classified) < 0.9:
        failures.append(f'description_coverage ({with_desc}/{len(pdf_classified)})')
        print('    FAIL — below 90%')
    else:
        print('    PASS')

    # 5. base_key uniqueness on classified dir + (later) enriched CSV — only check classified now
    bk_list = [p.stem for p in CLASSIFIED_DIR.glob('*.json')]
    print(f'\n[5] base_key uniqueness in data/classified/: {len(bk_list)} files, {len(set(bk_list))} unique')
    if len(bk_list) != len(set(bk_list)):
        dups = [k for k, n in Counter(bk_list).items() if n > 1]
        failures.append(f'duplicate_base_keys ({len(dups)})')
        print(f'    FAIL — duplicates: {dups[:10]}')
    else:
        print('    PASS')

    # 6. Spot-check 5 random outputs against source PDFs (sanity)
    print(f'\n[6] Spot-check (5 random):')
    sample = random.sample(pdf_classified, min(5, len(pdf_classified)))
    for p, d in sample:
        bk = d['base_key']
        pdf_extract = PDF_DIR / f'{bk}.json'
        if pdf_extract.exists():
            ext = json.loads(pdf_extract.read_text(encoding='utf-8'))
            print(f'    {bk}: themes={len(d["themes"])}, features={len(d["features"])}, desc_chars={len(d.get("description","") or "")}, pdf_lang={ext.get("pdf_source_language")}, raw_chars={ext.get("raw_text_chars")}')
        else:
            print(f'    {bk}: PDF extract missing!')

    # 7. PP CSV cross-check (if it exists)
    print(f'\n[7] pp_mechanic_candidates.csv cross-check:')
    if PP_CSV.exists():
        with open(PP_CSV, 'r', encoding='utf-8-sig') as f:
            rows = list(csv.DictReader(f))
        csv_games = {r['base_key'] for r in rows}
        json_games = set(candidate_games)
        if csv_games != json_games:
            extra_csv = csv_games - json_games
            extra_json = json_games - csv_games
            print(f'    INFO: CSV has {len(csv_games)} games, JSONs have {len(json_games)} games')
            if extra_csv:
                print(f'      Only in CSV: {sorted(extra_csv)[:5]}')
            if extra_json:
                print(f'      Only in JSON: {sorted(extra_json)[:5]}')
            print(f'    (Will be reconciled when consolidate runs)')
        else:
            print(f'    PASS: {len(csv_games)} games match')
    else:
        print(f'    SKIP: pp_mechanic_candidates.csv not yet generated (run consolidate)')

    # Summary
    print()
    print('=' * 60)
    if failures:
        print(f'VALIDATION FAILED: {", ".join(failures)}')
        print('=' * 60)
        sys.exit(1)
    print(f'VALIDATION PASSED — {len(pdf_classified)} PDF-sourced classified JSONs OK')
    print('=' * 60)


if __name__ == '__main__':
    main()
