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
| Session 5 — Re-run + AM_Masterlist join + PP taxonomy parity | ~450,000 | 1,228,000 |
| Session 6a — PDF enrichment (80 games) + PP candidate side-channel | ~480,000 | 1,708,000 |
| Session 6b — PDF enrichment SLOTS3 tail (54 games) | ~340,000 | 2,048,000 |

**Category split for Session 6a:** Feature 95% (PDF pipeline + PP side-channel + new market xlsx column), Bug fix 5% (per-market commercial-name lookup that fixed 85 unmatched folders). No Rework, no Cleanup.

**Budget status:** No `dev/ref/budget.md` exists yet — no per-session budget to compare against. Session 6a's 480k tokens used ~60% of the user's current 5-hour Max-plan window. Estimated 6b would push cumulative to ~105% if run back-to-back; **plan is to wait for window reset before 6b** (or split 6b into two sub-sessions).

**Context limits / splitting:** Session deliberately split per plan: 6a (this session, 80 NEW games) → hard pause → 6b (58 NEW games, fresh context) → 6c (47 backfills, fresh context). Did NOT hit context limits this session.

**File-size flag:** `main.py` is now **673 lines** (was 468 after Session 5; +200 from `cmd_extract_pdfs` + subparser wiring). Crosses the 500-line threshold. Suggest discussing a split next session — natural seams: (a) move each `cmd_*` function into `agents/cli/<command>.py` modules and keep `main.py` as the slim subparser entry point, or (b) split into `main_extract.py` / `main_classify.py` / `main_consolidate.py`. `agents/consolidator.py` is at 387, `agents/extractor.py` at 392, `agents/pdf_extractor.py` at 474 — all comfortably under.

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

### Session 5 — Re-run + AM_Masterlist join + PP taxonomy parity (Claude Code)
**Date:** 2026-04-28
**Status:** Complete
**Token category:** Feature

**What was done:**
- Recovered from lost outputs (`output/`, `data/raw_extracts/`, `data/classified/`, `POWERPOINTS/` all gone from disk).
- New PPTX folder downloaded to `data/01_Definicion Productos/` — partial: 62 game folders (MegaWays 11, Slots3 49, Boost&Win 2). Missing: Slots5, Bingo.
- Added `config/AM_Masterlist.xlsx` (6 market sheets, 503 rows total, 232 SPAIN). Used to attach current-live SEO spec data.
- **Code changes:** category normalization in `agents/extractor.py`; new `agents/am_masterlist.py` (load/match/gap-report); new `localise` subcommand in `main.py` (replaces broken API-based `cmd_classify`); 9 AM columns + gap-report write in `agents/consolidator.py`.
- **Pipeline re-run:** Phase 1 (62 extracts) → Phase 2 sub-agents (8 batches × 8 games × 3 waves of 3-3-2 parallel) → localise + AM enrichment → consolidate → HTML report.
- **Outputs:** `games_enriched.csv` (62 rows × 22 cols), `review_flagged.csv` (53 rows), `unknown_features_report.csv` (17), `am_spain_gap_report.csv` (197 rows = 232 AM Spain – 35 covered).
- New: `generate_market_xlsx.py` produces `output/themes_features_by_market.xlsx` — one sheet per AM market (SPAIN, PORTUGAL, .COM, NETHERLANDS, ITALY, COLOMBIA), all 503 AM rows preserved, themes/features populated where the localised name links via market_names.xlsx → base_key → enriched.
- **Taxonomy bumps**: v2.2 (added 'Ancient Civilisations' as explicit umbrella tag — was a category-only token previously). v2.3 (Pragmatic Play parity pass: 18 new themes added — Bees, Pigs, Chickens, Monkeys, Flowers, Phoenix, Goldmine, Cops & Robbers, Train, Scientist, John Hunter, Presidents, Brazil, Irish, Native American, Love, Queen, Cheese).
- **Consistency audit:** 0 unauthorised feature drift, 0 unauthorised theme drift after v2.2; all 12 celebrity-name tags compliant with co-occurrence rule.
- **PP mechanics review** generated as `output/missing_mechanics_review.xlsx` — 5 mechanics with English + Spanish descriptions for Product team review (Hyperplay, Increasing Wilds, Mystery Expanding Symbol, Powernudge, Super Scatter).

**Files created/modified:**
- `agents/extractor.py` — `_normalize_category` helper
- `agents/am_masterlist.py` — NEW
- `agents/consolidator.py` — extended with AM columns + gap report
- `main.py` — new `localise` subcommand, AM Masterlist arg on consolidate
- `config/seo_taxonomy.json` — v2.3
- `generate_market_xlsx.py` — NEW
- `generate_missing_mechanics_xlsx.py` — NEW
- `output/*.csv`, `output/themes_features_by_market.xlsx`, `output/missing_mechanics_review.xlsx`, `output/enrichment_report.html`

---

### Session 6a — PDF-based enrichment + PP candidate side-channel (Claude Code)
**Date:** 2026-04-28
**Status:** Complete. HARD-PAUSE per plan — resume 6b in fresh context via `/catchup`.
**Token category:** Feature

**What was done:**
- Built PDF pipeline: `agents/pdf_extractor.py` (walks 7-market FinalesProducto tree, 4-rule PDF discovery, pypdf+pdfplumber extraction, per-market commercial-name lookup that sidesteps the SPAIN/`.COM` cname quirk) + `extract-pdfs` subcommand in main.py + pypdf/pdfplumber added to requirements.
- Extended consolidator with `description`, `pdf_found`, `pdf_source_language` columns and a new `build_pp_candidate_report()` emitting `output/pp_mechanic_candidates.csv` (4 sanctioned PP mechanics, Powernudge excluded — it remaps to existing `Nudge & Hold`).
- `generate_market_xlsx.py` extended to 5 columns (Description added) with a fallback save-path when target file is open in Excel.
- Survey: 479 game folders scanned, 333 PDFs found, 185 unique base_keys with PDFs.
- Calibration: 1 sub-agent × 4 SLOTS5 EN games = 32k tokens (~8k/game) — far below 80k threshold.
- 80 NEW base_keys classified via 10 sub-agents in 4 waves (3-3-3-1). Schema/PP-leak/coverage validation all pass (`dev/validate_session6a.py`).
- 4 PP candidate hits captured in `output/pp_mechanic_candidates.csv`: 3× Increasing Wilds (Diamond Mine, Explosive Bandit 2, Explosive Wizard Cat), 1× Mystery Expanding Symbol (Dragons Double Pot). Evidence quotes are verbatim and look like genuine matches.

**Coverage delta** in `themes_features_by_market.xlsx`:
| Market | Pre | Post | Δ |
|---|---:|---:|---:|
| SPAIN | 39 | 83 | +44 |
| PORTUGAL | 11 | 42 | +31 |
| .COM | 9 | 57 | +48 |
| NETHERLANDS | 4 | 15 | +11 |
| ITALY | 6 | 23 | +17 |
| COLOMBIA | 0 | 8 | +8 |
| **Totals** | **69** | **228** | **+159** |

**Files created/modified:**
- `agents/pdf_extractor.py` (NEW)
- `agents/consolidator.py` (description, pp_candidate_report, pdf_found cols)
- `main.py` (extract-pdfs subcommand)
- `generate_market_xlsx.py` (Description col + Excel-locked fallback)
- `requirements.txt` (pypdf, pdfplumber)
- `dev/session6a_batches.py` (NEW — wave builder)
- `dev/validate_session6a.py` (NEW — validation gate)
- `dev/_session6a_batches/PROMPT_TEMPLATE.md` + 10 batch files (NEW)
- `data/pdf_extracts/*.json` (185 files, gitignored)
- `data/classified/*.json` (84 new this session, 146 total)
- `output/games_enriched.csv` (146 rows, 7 new cols)
- `output/themes_features_by_market.xlsx` (or `.LATEST.xlsx` if Excel was open)
- `output/pp_mechanic_candidates.csv` (NEW — 4 rows)
- `output/pdf_coverage_survey.csv` (NEW — 479 rows)
- `dev/ref/stage6a-summary.md` (NEW)

**Risks observed (non-blocking):**
- `localisation_resolver.match_extract_to_family` no-match for 51/146 — same SPAIN/.COM cname quirk. Cross-market deliverable still works (joins via AM directly). Fix in 6b if there's headroom.

---

### Session 6b — PDF enrichment SLOTS3 tail (Claude Code)
**Date:** 2026-04-28
**Status:** Complete. Run back-to-back with 6a (user opted in despite token-budget warning).
**Token category:** Feature 100%

**What was done:**
- Built `dev/session6b_batches.py` (clone of 6a builder, dedup-aware against existing classified set).
- Reused `dev/_session6a_batches/PROMPT_TEMPLATE.md` verbatim — only batch path changed.
- 54 NEW base_keys (50 SLOTS3 + 4 BINGO) → 7 batches → 3 waves (3-3-1).
- Validation: all 7 checks pass for 138 PDF-sourced JSONs.
- 0 PP candidate hits this session (total still 4, all from 6a). Confirms SLOTS3/BINGO PDFs typically don't describe the 4 sanctioned PP mechanics.
- Coverage: 228 → 278 enriched market rows (+50). SPAIN +44 (SLOTS3 is Spain-dominant); other markets +0–3.
- AM Spain gap: 152 → 110 rows (down 42).

**Files created/modified:**
- `dev/session6b_batches.py` (NEW)
- `dev/ref/stage6b-summary.md` (NEW)
- `data/classified/*.json` (54 new this session, 200 total)
- All `output/*.csv` and `output/themes_features_by_market.xlsx` refreshed
- `dev/projectlog.md` updated

**Note:** No code changes to the pipeline this session — pure classification work using infrastructure built in 6a.

---

## Current status
**Phase:** Sessions 6a + 6b complete. 138 of 138 NEW base_keys classified from PDFs. Only the 47 PDF backfills for Session-5-classified games remain (Session 6c, Description column only).
**Blocker:** None.
**Next action:** Session 6c — 47 PDF backfills. Run `/catchup` first if context cleared.

**Outstanding:**
1. Session 6c — 47 PDF backfills for Session-5 games (description column only; preserve themes/features unless material disagreement → log to `output/backfill_diffs.csv`). ~6 sub-agents in 2 waves, ~250k tokens.
2. Product team to review `output/missing_mechanics_review.xlsx` AND `output/pp_mechanic_candidates.csv` (4 hits) — confirm green-lit mechanics → bump taxonomy to v2.4 → re-classify affected games.
3. Optional: refactor `main.py` (now 673 lines) — split each `cmd_*` into `agents/cli/<command>.py`.
4. Optional: fix `localisation_resolver.match_extract_to_family` no-match for 52/200 (same SPAIN/.COM cname masking quirk that pdf_extractor sidesteps). Cross-market deliverable still works via the AM-direct path, so this is cosmetic.
5. Slots5/Bingo legacy PPTXs not yet downloaded — when they arrive, extractor picks them up via numeric-prefix pattern.
