# Stage 3 Summary — Consolidation + Output

## Output files generated
| File | Rows | Notes |
|------|------|-------|
| `output/games_enriched.csv` | 128 | Full dataset, flagged rows first |
| `output/review_flagged.csv` | 91 | Flagged subset + editor_notes column |
| `output/unknown_features_report.csv` | 51 | With suggested_standard_tag mappings |

## Review flag breakdown
| Reason | Count |
|--------|-------|
| feature_confidence < 0.75 | 57 |
| no_market_db_match | 39 |
| unknown_features present | 34 |
| theme_confidence < 0.75 | 23 |
| no_pptx_found | 7 |

Note: games can have multiple flag reasons; 91 unique games flagged out of 128 total.

## Taxonomy expansion (v1.0 → v2.0)
| New Tag | Category | Source count | Mapped from |
|---------|----------|-------------|-------------|
| Nudge & Hold | Respin & Hold | 7 | Avances, Retenciones, Paralo variants |
| Minigame | Minigames | 19 | Trilero, Ruleta, Pinball, etc. |
| Prize Ladder | Prize Mechanics | 3 | Suma Premio, Sube tu Premio |
| Gamble Feature | Prize Mechanics | 2 | Risk/Gamble, Deal or No Deal |
| Multi-Volatility | Volatility | 3 | MultiRatio, Multivolatilidad |
| Twin Spin | Volatility | 1 | Direct mechanic name |

35 new Spanish aliases added to `spanish_aliases.features`.

8 unknown features skipped as too game-specific (Siete Mixtos, Kisses, Esferas Sagradas, etc.).

## Category normalization
Mixed casing from different sources (folder names vs market DB) unified to uppercase:
- Slots3/SLOTS3 → SLOTS3 (91 games)
- Slots5/SLOTS5 → SLOTS5 (26 games)
- MegaWays/MEGAWAYS → MEGAWAYS (11 games)

## New CLI subcommands
- `consolidate` — reads classified JSONs, writes all 3 CSVs
- `merge-review --review PATH` — merges human-edited review CSV back
- `stats` — prints summary from games_enriched.csv
- `run-all --input PATH` — chains extract → classify → consolidate
