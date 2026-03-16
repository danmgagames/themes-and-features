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

**Outstanding before Session 1:**
- [ ] User to confirm PPTX folder Windows path format ✓ (confirmed: Windows path)
- [ ] User to confirm whether deactivated games should be included (default: skip)
- [ ] Obtain ANTHROPIC_API_KEY for Session 2 API calls

---

### Session 1 — Phase 1: Extractor (Claude Code)
**Date:** 2026-03-16
**Status:** Complete
**Category:** Feature
**Context limits hit:** No

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

**Outstanding for Session 2:**
- [ ] `market_names.xlsx` not in repo — market lookup skipped. Obtain file or skip market resolution.
- [ ] Obtain ANTHROPIC_API_KEY for classifier API calls
- [ ] 68 non-Comercial PPTXs lack structured category slides — classifier must work from raw text
- [ ] 10 games have no PPTX at all — flag for manual review

---

### Session 2 — Phase 2: Classifiers (Claude Code)
**Status:** Not started — blocked on Session 1
**Plan:**
- Paste `SESSION_2_PROMPT.md` into Claude Code
- Build theme, feature, localisation subagents
- Run `--dry-run` on 5 games, validate Spanish→English mapping
- Validate: "Robos"→Heist/Crime, "Megaways"→Megaways, "Compra Free Spins"→Buy Feature
- Full classify run (200–500 games, ~10 concurrent API calls)
- Record unknown_features found in `dev/ref/stage2-summary.md`

---

### Session 3 — Phase 3: Output + Review (Claude Code)
**Status:** Not started — blocked on Session 2
**Plan:**
- Paste `SESSION_3_PROMPT.md` into Claude Code
- Build consolidator, CSV output, review workflow, taxonomy expansion report
- Generate `output/games_enriched.csv` and `output/review_flagged.csv`
- Generate `output/unknown_features_report.csv`
- Extend `seo_taxonomy.json` based on unknown features found
- Record final stats in `dev/ref/stage3-summary.md`

---

## Current status
**Phase:** Phase 1 complete — extraction done, ready for Session 2 (classifiers)
**Blocker:** Need ANTHROPIC_API_KEY; market_names.xlsx missing (optional)
**Next action:** Run SESSION_2_PROMPT — build theme/feature classifiers, dry-run on 5 games
