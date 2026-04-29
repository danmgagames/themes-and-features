"""
Session 9 validation gate.

Checks the 4 web-sourced classified JSONs in data/classified_9/ for:
1. Schema integrity (required keys present)
2. PP leak check (no PP terms in features/unknown_features)
3. PP candidate sanctioned-only
4. Description coverage >= 90%
5. base_key uniqueness within classified_9/
6. base_key non-collision with already-classified data/classified/
   (intentional — Session 9 targets ONLY base_keys not yet in classified/)
7. Spot-check: 5 random outputs paired against their web_extract source

Exits non-zero if any required check fails.
"""

import json
import random
import sys
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
NEW_DIR = PROJECT_ROOT / 'data' / 'classified_9'
EXISTING_DIR = PROJECT_ROOT / 'data' / 'classified'
WEB_DIR = PROJECT_ROOT / 'data' / 'web_extracts'

PP_TERMS = ['Hyperplay', 'Increasing Wilds', 'Mystery Expanding Symbol', 'Super Scatter', 'Powernudge']
SANCTIONED_PP = {'Hyperplay', 'Increasing Wilds', 'Mystery Expanding Symbol', 'Super Scatter'}


def main():
    failures: list[str] = []
    print('=' * 60)
    print('Session 9 — validation gate')
    print('=' * 60)

    new_files = sorted(NEW_DIR.glob('*.json'))
    if not new_files:
        print(f'No JSONs found in {NEW_DIR.relative_to(PROJECT_ROOT)} — nothing to validate.')
        sys.exit(1)

    docs = []
    for p in new_files:
        try:
            d = json.loads(p.read_text(encoding='utf-8'))
            docs.append((p, d))
        except Exception as e:
            failures.append(f'parse_error {p.name}: {e}')

    print(f'\n[1] Schema integrity: {len(docs)} web-sourced classified JSONs')
    required = {'base_key', 'folder_category', 'description', 'web_found',
                'web_source_language', 'themes', 'features',
                'pp_candidate_mechanics', 'theme_confidence', 'feature_confidence'}
    schema_bad = []
    for p, d in docs:
        missing = required - d.keys()
        if missing:
            schema_bad.append((p.name, missing))
    if schema_bad:
        print(f'    FAIL: {len(schema_bad)} files missing required keys:')
        for name, missing in schema_bad[:5]:
            print(f'      {name}: missing {missing}')
        failures.append(f'schema_integrity ({len(schema_bad)} bad)')
    else:
        print('    PASS: all required keys present')

    leaks = []
    for p, d in docs:
        for t in PP_TERMS:
            if t in (d.get('features') or []):
                leaks.append((p.name, t, 'features'))
            if t in (d.get('unknown_features') or []):
                leaks.append((p.name, t, 'unknown_features'))
    print(f'\n[2] PP leak check: {len(leaks)} leaks')
    if leaks:
        print('    FAIL — leaks:')
        for name, t, where in leaks[:10]:
            print(f'      {name}: {t!r} in {where}')
        failures.append(f'pp_leak ({len(leaks)} leaks)')
    else:
        print('    PASS')

    bad_candidates = []
    candidate_count = 0
    candidate_games = []
    by_mech: Counter = Counter()
    for p, d in docs:
        cands = d.get('pp_candidate_mechanics') or []
        if cands:
            candidate_games.append(p.stem)
        for c in cands:
            candidate_count += 1
            mech = (c or {}).get('mechanic', '')
            by_mech[mech] += 1
            if mech not in SANCTIONED_PP:
                bad_candidates.append((p.name, mech))
    print(f'\n[3] Candidate capture: {candidate_count} entries across {len(candidate_games)} games')
    if bad_candidates:
        print('    FAIL — non-sanctioned mechanics:')
        for name, m in bad_candidates[:10]:
            print(f'      {name}: {m!r}')
        failures.append(f'pp_candidate_invalid ({len(bad_candidates)})')
    else:
        print('    PASS')
    if by_mech:
        for m, n in by_mech.most_common():
            print(f'      - {m}: {n}')

    with_desc = sum(1 for _, d in docs if (d.get('description') or '').strip())
    print(f'\n[4] Description coverage: {with_desc}/{len(docs)}')
    if docs and with_desc / len(docs) < 0.9:
        failures.append(f'description_coverage ({with_desc}/{len(docs)})')
        print('    FAIL — below 90%')
    else:
        print('    PASS')

    bks = [p.stem for p in new_files]
    print(f'\n[5] base_key uniqueness in classified_9/: {len(bks)} files, {len(set(bks))} unique')
    if len(bks) != len(set(bks)):
        dups = [k for k, n in Counter(bks).items() if n > 1]
        failures.append(f'duplicate_base_keys ({len(dups)})')
        print(f'    FAIL — duplicates: {dups[:10]}')
    else:
        print('    PASS')

    existing = {p.stem for p in EXISTING_DIR.glob('*.json')}
    new = set(bks)
    overlap = existing & new
    print(f'\n[6] Non-collision with data/classified/: existing {len(existing)}, new {len(new)}, overlap {len(overlap)}')
    if overlap:
        print(f'    WARN — overlap (will be overwritten by merge): {sorted(overlap)[:5]}')
    else:
        print('    PASS')

    print('\n[7] Spot-check (5 random):')
    sample = random.sample(docs, min(5, len(docs)))
    for p, d in sample:
        bk = d['base_key']
        web_extract = WEB_DIR / f'{bk}.json'
        if web_extract.exists():
            ext = json.loads(web_extract.read_text(encoding='utf-8'))
            print(f'    {bk}: themes={len(d["themes"])}, features={len(d["features"])}, '
                  f'desc_chars={len(d.get("description","") or "")}, '
                  f'src_lang={d.get("web_source_language")}, '
                  f'src_chars={ext.get("raw_text_chars")}')
        else:
            print(f'    {bk}: web_extract missing!')

    print()
    print('=' * 60)
    if failures:
        print(f'VALIDATION FAILED: {", ".join(failures)}')
        print('=' * 60)
        sys.exit(1)
    print(f'VALIDATION PASSED — {len(docs)} web-sourced classified JSONs OK')
    print('=' * 60)


if __name__ == '__main__':
    main()
