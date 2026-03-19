# Game Enrichment Pipeline — Project Log

## Project overview
Extract Themes and Main Features from 200–500 MGA game PowerPoint decks,
standardise against a market-aligned SEO taxonomy, resolve localisation variants,
output an enriched CSV for casino site SEO.

## Token usage
| Session | Tokens used | Cumulative |
|---------|------------|------------|
| Planning (Claude.ai) | ~18,000 | 18,000 |
| Session 1 — Extractor (Feature) | ~35,000 | 53,000 |
| Session 2a — Classifier scaffolding + test | ~80,000 | 133,000 |
| Session 2b — Full classification run (Feature) | ~530,000 | 663,000 |
| Session 3 — Consolidation + taxonomy (Feature) | ~75,000 | 738,000 |
| Session 4 — Human review merge + report (Feature) | ~40,000 | 778,000 |

---

## Session log

### Session 0 — Planning (Claude.ai, not Claude Code)
**Status:** Complete
**What was done:**
- Analysed MGA_Products.xlsx: 700 rows, 357 game families, 8 markets
- Analysed sample PPTX (Take the Money Megaways): 3-slide "Comercial" structure
- Analysed Pragmatic Play competitor taxonomy for market-standard SEO theme labels
- Designed full 3-phase pipeline architecture (Extract → Classify → Consolidate)
- Decided: themes from Pragmatic taxonomy; features from MGA PPTX extraction pass
- Decided: celebrity tags stacked (Celebrities + name + sport/field)
- Decided: Movies & TV tag + genre tag applied together where relevant
- Decided: Sport and Celebrities split (not combined) for SEO surface area
- Created all project scaffold files

**Files created:**
- `CLAUDE.md` — project memory (system prompts, schema, thresholds, Spanish aliases)
- `config/seo_taxonomy.json` — seed taxonomy (themes + features + spanish_aliases)
- `config/market_names.xlsx` — master localisation DB (copied from source)
- `SESSION_1_PROMPT.md` — Claude Code prompt for Phase 1 (extractor)
- `SESSION_2_PROMPT.md` — Claude Code prompt for Phase 2 (classifiers)
- `SESSION_3_PROMPT.md` — Claude Code prompt for Phase 3 (output + review)
- `test_data/SLOTS/TAKE_THE_MONEY_MEGAWAYS/` — sample PPTX for testing

**Key findings recorded in:** `dev/ref/architecture.md`, `dev/ref/taxonomy-decisions.md`

---

### Session 1 — Phase 1: Extractor (Claude Code)
**Date:** 2026-03-16
**Status:** Complete

**What was done:**
- Built `agents/extractor.py` (246 lines) and `main.py` (92 lines)
- Created `requirements.txt` with pinned deps
- Adapted to real folder structure (differs from plan — see stage1-summary)
- Ran full extraction: 128 unique games, 121 with PPTXs, 51/53 Comercial files with category slide
- Broadened slide detection to catch "TEMÁTICAS" and "CARACTERISTICAS" headers (newer PPTX format)

**Files created/modified:**
- `agents/__init__.py`, `agents/extractor.py`, `main.py`, `requirements.txt`
- `data/raw_extracts/*.json` (128 files, gitignored)

**Key findings:** recorded in `dev/ref/stage1-summary.md`

---

### Session 2a — Phase 2 scaffolding + architecture pivot (Claude Code)
**Date:** 2026-03-16
**Status:** Complete — scaffolding done, architecture updated, ready for classification run

**What was done:**
- Built `agents/theme_classifier.py`, `agents/feature_classifier.py`, `agents/localisation_resolver.py`
- Wired `classify` subcommand into `main.py` (with --dry-run, --include-deactivated flags)
- Attempted API dry-run — API key had no model access (404 on all models)
- **Architecture pivot:** switched from Claude API calls to Claude Code sub-agent approach
  - Each sub-agent processes a batch of 10 games using Max plan tokens
  - 13 sub-agents total, run 3–4 in parallel
  - No API key or credits required
- Ran manual test classification on 5 Megaways games (Option A: classify in-conversation)
- Test results validated: themes/features/confidence scores look correct
- `config/market_names.xlsx` now in repo — localisation resolver tested, found 341 active families
- Celebrity IP detection working: found Charlie Riina, Lisa Mancini, Joshua Guvi, Ron Josol, Taya Valkyrie
- Deleted `.env` file (no longer needed — no API calls)
- Updated `SESSION_2_PROMPT.md` to reflect sub-agent approach
- Updated `dev/ref/architecture.md` with new Phase 2 design

**Unknown features found in test batch:**
- Risk/Gamble Free Spins
- Roulette Free Spins Selection
- MultiRatio/MultiVolatility

**Files created/modified:**
- `agents/theme_classifier.py` (new — reference/prompts, not used directly)
- `agents/feature_classifier.py` (new — reference/prompts, not used directly)
- `agents/localisation_resolver.py` (new — deterministic lookup, used directly)
- `main.py` (updated — classify subcommand added)
- `data/classified/*.json` (5 test files)
- `dev/SessionPrompts/SESSION_2_PROMPT.md` (updated for sub-agent approach)
- `dev/ref/architecture.md` (updated)

---

### Session 2b — Phase 2: Full classification run (Claude Code)
**Date:** 2026-03-16
**Status:** Complete

**What was done:**
- Classified all 128 games via 13 Claude Code sub-agents (batches of 10)
- Ran sub-agents in 3 waves: wave 1 (4 parallel), wave 2 (4 parallel), wave 3 (5 parallel)
- Ran localisation resolver in main context — merged market data into all classified JSONs
- Validated results: 128 classified, 89 matched to market DB, 39 unmatched

**Classification stats:**
- 89/128 matched to market_names.xlsx families, 39 unmatched (will be flagged)
- 23 games with theme confidence < 0.75 (mostly design-only PPTXs)
- 57 games with feature confidence < 0.75 (Slots3 design PPTXs lack mechanic detail)
- 7 games with no PPTX found
- 34 games with unknown features — 51 unique unknown mechanics captured
- 5 celebrity IPs from Ca/Se variants (Charlie Riina, Lisa Mancini, Joshua Guvi, Ron Josol, Taya Valkyrie)
- Many additional celebrities detected from game names (Chiquito de la Calzada, Samantha Fox, Mario Vaquerizo, etc.)

**Token breakdown:** ~490k sub-agents + ~40k main context = ~530k (Feature)

**Files modified:**
- `data/classified/*.json` (128 files, gitignored)

**Key findings:** recorded in `dev/ref/stage2-summary.md`

---

### Session 3 — Phase 3: Consolidation + Output (Claude Code)
**Date:** 2026-03-16
**Status:** Complete
**Token category:** Feature

**What was done:**
- Built `agents/consolidator.py` (242 lines) — loads classified JSONs, builds review flags, writes CSVs
- Added 4 new subcommands to `main.py`: `consolidate`, `merge-review`, `stats`, `run-all`
- Generated all 3 output CSVs (UTF-8-BOM, pipe-separated multi-values, sorted flagged-first)
- Normalized category casing (SLOTS3/Slots3 → SLOTS3)
- Generated unknown features report with suggested mappings (via sub-agent)
- Expanded `seo_taxonomy.json` v2.0: 6 new tags, 35 new Spanish aliases
- Tested merge-review round-trip successfully
- Updated CLAUDE.md with new commands + taxonomy maintenance docs

**Output stats:**
- 128 games → `games_enriched.csv`
- 91 flagged → `review_flagged.csv` (57 low feature conf, 39 no market match, 34 unknown features, 23 low theme conf, 7 no PPTX)
- 51 unknown features → `unknown_features_report.csv` (mapped to 6 new + 5 existing tags, 8 skipped)

**New taxonomy tags:** Nudge & Hold, Minigame, Prize Ladder, Gamble Feature, Multi-Volatility, Twin Spin

**Files created/modified:**
- `agents/consolidator.py` (new)
- `main.py` (updated — 4 new subcommands, 468 lines)
- `config/seo_taxonomy.json` (updated — v2.0, 360 lines)
- `CLAUDE.md` (updated — new commands, taxonomy maintenance section)
- `output/*.csv` (3 files, gitignored)

**Key findings:** recorded in `dev/ref/stage3-summary.md`

---

### Session 4 — Human review feedback + HTML report (Claude Code)
**Date:** 2026-03-19
**Status:** Complete
**Token category:** Feature

**What was done:**
- Applied 3 human review feedback items to consolidator pipeline:
  1. SLOTS3 default features: all 91 SLOTS3 games now auto-receive Mini-Games, Bonos Superiores, Dual-Screen Layout
  2. Feature dedup: "Bonus Round" removed when "Bonus Game" present
  3. Renamed "Free Spins" → "Free Rounds" across taxonomy + consolidator
- Updated `seo_taxonomy.json` to v2.1 (renames, new SLOTS3 Standard category, removed Bonus Round from tag list)
- Added `normalize_features()` to consolidator — applies renames, dedup, and SLOTS3 defaults at consolidation time
- Merged 91 human-reviewed rows back into enriched CSV (0 still flagged)
- Built `generate_report.py` → `output/enrichment_report.html` (dark theme, bar charts, EN/ES toggle)

**Files created/modified:**
- `agents/consolidator.py` (modified — added normalize_features, 285 lines)
- `config/seo_taxonomy.json` (modified — v2.1, 364 lines)
- `generate_report.py` (new — HTML report generator)
- `output/enrichment_report.html` (new, gitignored)

---

## Current status
**Phase:** Pipeline complete — all games enriched, human review merged, report generated
**Blocker:** None
**Next action:** Team reviews `output/enrichment_report.html` to decide final tag set. Then finalize taxonomy if changes needed.
