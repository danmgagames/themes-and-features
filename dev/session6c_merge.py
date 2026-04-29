"""
Session 6c merge + diff post-processor.

For each JSON in data/classified_6c/:
  1. Load the corresponding Session-5 classification from data/classified/
  2. Add `description`, `pdf_source_language`, `pdf_found`, `pp_candidate_mechanics`
     from the 6c output (Session 5 stays authoritative on themes/features).
  3. If both classifications report theme_confidence >= 0.85 AND the theme
     tag-set differs (or same for features), log a row to backfill_diffs.csv.
  4. Write the merged JSON back to data/classified/<base_key>.json.

Backfill_diffs.csv schema:
    base_key, kind (themes|features), s5_tags, s6c_tags,
    only_in_s5, only_in_s6c, s5_conf, s6c_conf
"""

import csv
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CLASSIFIED_DIR = PROJECT_ROOT / 'data' / 'classified'
S6C_DIR = PROJECT_ROOT / 'data' / 'classified_6c'
DIFFS_CSV = PROJECT_ROOT / 'output' / 'backfill_diffs.csv'

CONF_THRESHOLD = 0.85


def main():
    DIFFS_CSV.parent.mkdir(parents=True, exist_ok=True)

    diffs: list[dict] = []
    merged_count = 0
    missing_s5 = []

    for p in sorted(S6C_DIR.glob('*.json')):
        s6c = json.loads(p.read_text(encoding='utf-8'))
        bk = s6c['base_key']
        s5_path = CLASSIFIED_DIR / f'{bk}.json'
        if not s5_path.exists():
            missing_s5.append(bk)
            continue
        s5 = json.loads(s5_path.read_text(encoding='utf-8'))

        # Merge: pull description-side fields from 6c, keep S5 themes/features.
        s5['description'] = s6c.get('description', '')
        s5['pdf_source_language'] = s6c.get('pdf_source_language', '')
        s5['pdf_found'] = bool(s6c.get('pdf_found', True))
        s5['pp_candidate_mechanics'] = s6c.get('pp_candidate_mechanics', [])
        # Preserve 6c notes if any (e.g. "missing_description")
        s6c_notes = s6c.get('notes') or []
        if s6c_notes:
            existing = s5.get('notes') or []
            if not isinstance(existing, list):
                existing = []
            for n in s6c_notes:
                if n not in existing:
                    existing.append(n)
            s5['notes'] = existing

        # Diff detection
        s5_themes = set(s5.get('themes') or [])
        s6c_themes = set(s6c.get('themes') or [])
        s5_features = set(s5.get('features') or [])
        s6c_features = set(s6c.get('features') or [])

        s5_t_conf = float(s5.get('theme_confidence') or 0)
        s6c_t_conf = float(s6c.get('theme_confidence') or 0)
        s5_f_conf = float(s5.get('feature_confidence') or 0)
        s6c_f_conf = float(s6c.get('feature_confidence') or 0)

        if s5_themes != s6c_themes and s5_t_conf >= CONF_THRESHOLD and s6c_t_conf >= CONF_THRESHOLD:
            diffs.append({
                'base_key': bk,
                'kind': 'themes',
                's5_tags': '|'.join(sorted(s5_themes)),
                's6c_tags': '|'.join(sorted(s6c_themes)),
                'only_in_s5': '|'.join(sorted(s5_themes - s6c_themes)),
                'only_in_s6c': '|'.join(sorted(s6c_themes - s5_themes)),
                's5_conf': f'{s5_t_conf:.2f}',
                's6c_conf': f'{s6c_t_conf:.2f}',
            })

        if s5_features != s6c_features and s5_f_conf >= CONF_THRESHOLD and s6c_f_conf >= CONF_THRESHOLD:
            diffs.append({
                'base_key': bk,
                'kind': 'features',
                's5_tags': '|'.join(sorted(s5_features)),
                's6c_tags': '|'.join(sorted(s6c_features)),
                'only_in_s5': '|'.join(sorted(s5_features - s6c_features)),
                'only_in_s6c': '|'.join(sorted(s6c_features - s5_features)),
                's5_conf': f'{s5_f_conf:.2f}',
                's6c_conf': f'{s6c_f_conf:.2f}',
            })

        s5_path.write_text(json.dumps(s5, indent=2, ensure_ascii=False), encoding='utf-8')
        merged_count += 1

    # Write diffs CSV
    fields = ['base_key', 'kind', 's5_tags', 's6c_tags', 'only_in_s5', 'only_in_s6c', 's5_conf', 's6c_conf']
    with open(DIFFS_CSV, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for d in sorted(diffs, key=lambda x: (x['kind'], x['base_key'])):
            w.writerow(d)

    print(f'Merged: {merged_count} files')
    print(f'Disagreements logged: {len(diffs)} rows -> {DIFFS_CSV.relative_to(PROJECT_ROOT)}')
    if missing_s5:
        print(f'WARNING: {len(missing_s5)} 6c outputs had no Session-5 counterpart: {missing_s5[:5]}')

    # Per-kind breakdown
    by_kind: dict[str, int] = {}
    for d in diffs:
        by_kind[d['kind']] = by_kind.get(d['kind'], 0) + 1
    for k, n in sorted(by_kind.items()):
        print(f'  {k}: {n}')


if __name__ == '__main__':
    main()
