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

### Session 3 — Phase 3: Output + Review (Claude Code)
**Status:** Not started — next session
**Plan:**
- Follow `SESSION_3_PROMPT.md`
- Build consolidator, CSV output, review workflow, taxonomy expansion report
- Generate `output/games_enriched.csv` and `output/review_flagged.csv`
- Generate `output/unknown_features_report.csv`
- Extend `seo_taxonomy.json` based on unknown features found
- Record final stats in `dev/ref/stage3-summary.md`

---

## Current status
**Phase:** Phase 2 complete — all 128 games classified and localisation-resolved
**Blocker:** None
**Next action:** Session 3 — first validate/QA the classification results thoroughly, then read SESSION_3_PROMPT and proceed to Phase 3 (consolidator, CSVs, unknown features report)
