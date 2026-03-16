# Game Enrichment Pipeline — Project Log

## Project overview
Extract Themes and Main Features from 200–500 MGA game PowerPoint decks,
standardise against a market-aligned SEO taxonomy, resolve localisation variants,
output an enriched CSV for casino site SEO.

## Token usage
| Session | Tokens used | Cumulative |
|---------|------------|------------|
| Planning (Claude.ai) | ~18,000 | 18,000 |

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
**Status:** Not started
**Plan:**
- Paste `SESSION_1_PROMPT.md` into Claude Code
- Build `agents/extractor.py` and `main.py extract` subcommand
- Test against sample PPTX in `test_data/`
- Note match rate on `market_names.xlsx` fuzzy lookup — if < 80%, normalise folder names first

**Watch for:**
- How many Spain-only games don't fuzzy-match (affects Session 2 cost)
- Any PPTX structures that differ significantly from the 3-slide sample
- Record findings in `dev/ref/stage1-summary.md`

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
**Phase:** Pre-development — scaffold complete, ready for Session 1
**Blocker:** None — ready to start
**Next action:** Open Claude Code, place project files, paste SESSION_1_PROMPT.md
