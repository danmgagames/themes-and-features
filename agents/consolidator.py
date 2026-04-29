"""
Phase 3: Consolidation and CSV output.

Reads classified JSONs, builds review flags, writes games_enriched.csv,
review_flagged.csv, and unknown_features_report.csv.
"""

import csv
import json
import logging
from collections import Counter
from pathlib import Path

logger = logging.getLogger(__name__)

CONFIDENCE_THRESHOLD = 0.75

# SLOTS3 games always get these default features
SLOTS3_DEFAULT_FEATURES = ['Mini-Games', 'Bonos Superiores', 'Dual-Screen Layout']

# Feature renames applied to all games
FEATURE_RENAMES = {
    'Free Spins': 'Free Rounds',
    'Minigame': 'Mini-Games',
}

# Sanctioned PP candidate mechanics (Powernudge is intentionally excluded —
# it remaps to the existing 'Nudge & Hold' tag in the classifier prompt).
SANCTIONED_PP_MECHANICS = {
    'Hyperplay',
    'Increasing Wilds',
    'Mystery Expanding Symbol',
    'Super Scatter',
}


def normalize_features(features: list[str], category: str) -> list[str]:
    """Apply feature normalization rules from human review feedback.

    1. Rename tags (Free Spins → Free Rounds, Minigame → Mini-Games)
    2. Deduplicate: drop 'Bonus Round' when 'Bonus Game' is present
    3. Add SLOTS3 default features for SLOTS3 category games
    """
    # Apply renames
    features = [FEATURE_RENAMES.get(f, f) for f in features]

    # Deduplicate Bonus Game / Bonus Round
    if 'Bonus Game' in features and 'Bonus Round' in features:
        features = [f for f in features if f != 'Bonus Round']

    # Add SLOTS3 defaults
    if category.upper() == 'SLOTS3':
        for default in SLOTS3_DEFAULT_FEATURES:
            if default not in features:
                features.append(default)

    # Remove any exact duplicates while preserving order
    seen = set()
    deduped = []
    for f in features:
        if f not in seen:
            seen.add(f)
            deduped.append(f)

    return deduped

AM_COLUMNS = [
    'am_tier', 'am_release_date', 'am_rtp', 'am_volatility',
    'am_max_multiplier', 'am_pay_lines', 'am_reels', 'am_demo_url',
    'am_match_method',
]

OUTPUT_COLUMNS = [
    'base_key', 'es_commercial_name', 'category', 'markets', 'themes',
    'features', 'description', 'celebrity_names',
    'theme_confidence', 'feature_confidence',
    'localisation_match_confidence', 'pptx_found', 'pdf_found',
    'pdf_source_language', 'web_found', 'web_source_language',
    *AM_COLUMNS,
    'review_flag', 'review_reason',
]

PP_CANDIDATE_COLUMNS = [
    'base_key', 'es_commercial_name', 'category', 'markets',
    'suggested_pp_mechanics', 'evidence_quotes', 'pdf_source_language',
]

GAP_REPORT_COLUMNS = [
    'commercial_name', 'category', 'tier', 'release_date',
    'volatility', 'rtp', 'demo_url', 'notes',
]


def load_classified(classified_dir: Path) -> list[dict]:
    """Load all classified JSON files from a directory."""
    results = []
    for f in sorted(classified_dir.glob('*.json')):
        with open(f, 'r', encoding='utf-8') as fh:
            results.append(json.load(fh))
    return results


def build_row(game: dict) -> dict:
    """Convert a classified game dict into a CSV row dict with review flags."""
    reasons = []

    theme_conf = game.get('theme_confidence', 0.0) or 0.0
    feature_conf = game.get('feature_confidence', 0.0) or 0.0
    loc_conf = game.get('localisation_match_confidence', 0.0) or 0.0
    pptx_found = game.get('pptx_found', False)

    if theme_conf < CONFIDENCE_THRESHOLD:
        reasons.append(f'theme_confidence={theme_conf:.2f}')
    if feature_conf < CONFIDENCE_THRESHOLD:
        reasons.append(f'feature_confidence={feature_conf:.2f}')
    if loc_conf < CONFIDENCE_THRESHOLD and loc_conf > 0:
        reasons.append(f'localisation_match_confidence={loc_conf:.2f}')
    if not pptx_found:
        reasons.append('no_pptx_found')
    if game.get('localisation_match_method') == 'none':
        reasons.append('no_market_db_match')
    if game.get('unknown_features'):
        reasons.append(f'unknown_features: {", ".join(game["unknown_features"])}')

    am_match_method = game.get('am_match_method', 'none')
    loc_method = game.get('localisation_match_method', '')
    if am_match_method == 'none' and loc_method and loc_method != 'none':
        reasons.append('no_am_masterlist_match')

    review_flag = len(reasons) > 0

    category = (game.get('category') or '').upper()
    features = normalize_features(game.get('features', []), category)

    row = {
        'base_key': game.get('base_key', ''),
        'es_commercial_name': game.get('es_commercial_name') or '',
        'category': category,
        'markets': '|'.join(game.get('markets', [])),
        'themes': '|'.join(game.get('themes', [])),
        'features': '|'.join(features),
        'description': game.get('description') or '',
        'celebrity_names': '|'.join(game.get('celebrity_names', [])),
        'theme_confidence': theme_conf,
        'feature_confidence': feature_conf,
        'localisation_match_confidence': loc_conf,
        'pptx_found': pptx_found,
        'pdf_found': game.get('pdf_found', False),
        'pdf_source_language': game.get('pdf_source_language') or '',
        'web_found': game.get('web_found', False),
        'web_source_language': game.get('web_source_language') or '',
        'review_flag': review_flag,
        'review_reason': '; '.join(reasons) if reasons else '',
    }
    for col in AM_COLUMNS:
        row[col] = game.get(col, '')
    return row


def build_pp_candidate_report(games: list[dict]) -> list[dict]:
    """
    Aggregate sub-agent-suggested Pragmatic Play mechanic candidates per game.

    Filters strictly to the 4 sanctioned strings (Powernudge intentionally
    excluded — it remaps to 'Nudge & Hold' upstream). Anything else is
    dropped defensively, even if a sub-agent slips it past the prompt.
    """
    rows = []
    for game in games:
        candidates = game.get('pp_candidate_mechanics') or []
        if not isinstance(candidates, list) or not candidates:
            continue

        accepted = []
        for c in candidates:
            if not isinstance(c, dict):
                continue
            mechanic = str(c.get('mechanic', '') or '').strip()
            if mechanic not in SANCTIONED_PP_MECHANICS:
                continue
            quote = str(c.get('evidence_quote', '') or '').strip()[:200]
            accepted.append((mechanic, quote))

        if not accepted:
            continue

        mechanics = sorted({m for m, _ in accepted})
        quotes = [f"[{m}] {q}" for m, q in accepted if q]

        rows.append({
            'base_key': game.get('base_key', ''),
            'es_commercial_name': game.get('es_commercial_name') or '',
            'category': (game.get('category') or '').upper(),
            'markets': '|'.join(game.get('markets', [])),
            'suggested_pp_mechanics': '|'.join(mechanics),
            'evidence_quotes': ' || '.join(quotes),
            'pdf_source_language': game.get('pdf_source_language') or '',
        })

    rows.sort(key=lambda r: (r['suggested_pp_mechanics'], r['base_key']))
    return rows


def sort_rows(rows: list[dict]) -> list[dict]:
    """Sort: review_flag=True first, then alphabetically by es_commercial_name."""
    return sorted(rows, key=lambda r: (
        not r['review_flag'],  # True first (not True = False, sorts before not False = True)
        (r['es_commercial_name'] or r['base_key']).lower(),
    ))


def write_csv(rows: list[dict], output_path: Path, columns: list[str]):
    """Write rows to CSV with UTF-8-BOM encoding."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)


def build_unknown_features_report(games: list[dict]) -> list[dict]:
    """Aggregate unknown features across all games."""
    feature_games = {}  # feature -> list of game names
    for game in games:
        for uf in game.get('unknown_features', []):
            if uf not in feature_games:
                feature_games[uf] = []
            name = game.get('es_commercial_name') or game.get('base_key', '')
            if name not in feature_games[uf]:
                feature_games[uf].append(name)

    report = []
    for feature, game_list in feature_games.items():
        report.append({
            'unknown_feature': feature,
            'count': len(game_list),
            'example_games': '|'.join(game_list[:5]),
            'suggested_standard_tag': '',
        })

    report.sort(key=lambda r: -r['count'])
    return report


def consolidate(classified_dir: Path, output_dir: Path, am_masterlist_path: Path | None = None) -> dict:
    """
    Main consolidation entry point.
    Returns stats dict.
    """
    games = load_classified(classified_dir)
    logger.info(f"Loaded {len(games)} classified games")

    rows = [build_row(g) for g in games]
    rows = sort_rows(rows)

    # Write games_enriched.csv
    enriched_path = output_dir / 'games_enriched.csv'
    write_csv(rows, enriched_path, OUTPUT_COLUMNS)

    # Write review_flagged.csv (with extra editor_notes column)
    flagged = [r for r in rows if r['review_flag']]
    flagged_rows = [{**r, 'editor_notes': ''} for r in flagged]
    review_path = output_dir / 'review_flagged.csv'
    write_csv(flagged_rows, review_path, OUTPUT_COLUMNS + ['editor_notes'])

    # Write unknown features report
    report = build_unknown_features_report(games)
    report_path = output_dir / 'unknown_features_report.csv'
    write_csv(report, report_path, ['unknown_feature', 'count', 'example_games', 'suggested_standard_tag'])

    # Write PP candidate report (Pragmatic Play mechanics suggested but not in taxonomy)
    pp_candidate_rows = build_pp_candidate_report(games)
    pp_candidate_path = output_dir / 'pp_mechanic_candidates.csv'
    write_csv(pp_candidate_rows, pp_candidate_path, PP_CANDIDATE_COLUMNS)

    # Write AM Spain gap report (games in AM Masterlist with no PPTX coverage)
    gap_path = output_dir / 'am_spain_gap_report.csv'
    gap_rows = []
    if am_masterlist_path and am_masterlist_path.exists():
        from agents.am_masterlist import load_am_spain, build_gap_report
        am_rows = load_am_spain(am_masterlist_path)
        gap_rows = build_gap_report(am_rows, games)
        write_csv(gap_rows, gap_path, GAP_REPORT_COLUMNS)

    # Compute stats
    total = len(rows)
    flagged_count = len(flagged)
    pptx_found = sum(1 for r in rows if r['pptx_found'])
    pptx_missing = total - pptx_found

    # Theme/feature counts
    theme_counter = Counter()
    feature_counter = Counter()
    for r in rows:
        for t in r['themes'].split('|'):
            t = t.strip()
            if t:
                theme_counter[t] += 1
        for f in r['features'].split('|'):
            f = f.strip()
            if f:
                feature_counter[f] += 1

    # Category/market counts
    category_counter = Counter()
    market_counter = Counter()
    for r in rows:
        if r['category']:
            category_counter[r['category']] += 1
        for m in r['markets'].split('|'):
            m = m.strip()
            if m:
                market_counter[m] += 1

    # Review reason breakdown
    reason_counter = Counter()
    for r in flagged:
        for reason in r['review_reason'].split('; '):
            # Normalize: just the reason type
            key = reason.split('=')[0].split(':')[0].strip()
            if key:
                reason_counter[key] += 1

    stats = {
        'total': total,
        'flagged': flagged_count,
        'pptx_found': pptx_found,
        'pptx_missing': pptx_missing,
        'top_themes': theme_counter.most_common(10),
        'top_features': feature_counter.most_common(10),
        'categories': category_counter.most_common(),
        'markets': market_counter.most_common(),
        'review_reasons': reason_counter.most_common(),
        'unknown_features_count': len(report),
        'pp_candidates_count': len(pp_candidate_rows),
        'gap_report_count': len(gap_rows),
        'enriched_path': str(enriched_path),
        'review_path': str(review_path),
        'report_path': str(report_path),
        'pp_candidate_path': str(pp_candidate_path),
        'gap_report_path': str(gap_path),
    }

    return stats


def merge_review(review_csv: Path, enriched_csv: Path) -> dict:
    """
    Merge human-edited review CSV back into games_enriched.csv.
    Returns stats dict.
    """
    # Read review rows
    with open(review_csv, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        review_rows = {r['base_key']: r for r in reader}

    # Read existing enriched rows
    with open(enriched_csv, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        enriched_rows = list(reader)

    merged_count = 0
    still_flagged = 0

    for i, row in enumerate(enriched_rows):
        if row['base_key'] in review_rows:
            reviewed = review_rows[row['base_key']]
            # Overwrite with reviewed data
            for col in OUTPUT_COLUMNS:
                if col in reviewed:
                    enriched_rows[i][col] = reviewed[col]
            enriched_rows[i]['review_flag'] = 'False'
            enriched_rows[i]['review_reason'] = 'human_reviewed'
            merged_count += 1

    still_flagged = sum(1 for r in enriched_rows if r['review_flag'] == 'True')

    # Re-sort and write
    enriched_rows.sort(key=lambda r: (
        r['review_flag'] != 'True',
        (r['es_commercial_name'] or r['base_key']).lower(),
    ))

    write_csv(enriched_rows, enriched_csv, OUTPUT_COLUMNS)

    return {
        'merged': merged_count,
        'still_flagged': still_flagged,
    }
