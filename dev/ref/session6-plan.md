# Session 6 plan — PDF-based enrichment of tagless market rows

## Goal
Fill in themes/features **and a new English Description blurb** for the ~440 currently-tagless rows in `output/themes_features_by_market.xlsx` by reading "Descripcion del juego" PDFs from the `X:\DivisionOnline\FinalesProducto` network share.

After Session 5, themes/features are populated for 69 of 503 AM rows (the games whose PPTX decks were in the partial download). The remaining rows have empty Themes / Features columns. This session enriches them from PDFs instead of PPTXs.

## Source folder
`X:\DivisionOnline\FinalesProducto\<MARKET>\<CATEGORY>\<GameName>\`

Where MARKET ∈ {ESPAÑA, PORTUGAL, ITALIA, COLOMBIA, PAISES BAJOS, OTROS MERCADOS, TODOS MERCADOS} and CATEGORY ∈ {BINGO, MEGAWAYS, SLOTS3, SLOTS5}.

## PDF discovery rules

Per game folder, find the description PDF in this priority order:

1. **`Marketing Assets/06. Descripcion del juego/*.pdf`** (SLOTS5 convention — `*_GameDescription_ENG.pdf`)
2. **`Gamesheets/*Descripcion del juego.pdf`** or **`Gamesheets/descripcion_juego_*.pdf`** (BINGO convention)
3. **Any subfolder named `descripcion/`** containing `descripcion_juego_*.pdf`
4. **Fallback:** any PDF anywhere under the game folder whose filename matches case-insensitive `descripcion.juego` (with optional separators).

**Language priority:** prefer files with `_ENG` or `_EN` in the name; fall back to `_ESP` / `_ES`; last resort `_BZL` (Brazilian Portuguese — generally skip unless nothing else).

## Mapping rows to game folders

`themes_features_by_market.xlsx` has GameName + Category per market sheet. The market sheet name maps to the `FinalesProducto` market subdir:

| Sheet | FinalesProducto folder |
|---|---|
| SPAIN | ESPAÑA |
| PORTUGAL | PORTUGAL |
| .COM | TODOS MERCADOS or OTROS MERCADOS (try both) |
| NETHERLANDS | PAISES BAJOS |
| ITALY | ITALIA |
| COLOMBIA | COLOMBIA |

GameName matching to folder name needs fuzzy matching (rapidfuzz token_sort_ratio ≥ 85) because folder names use different casing/punctuation than the AM masterlist names.

## Pipeline (mirrors Session 2 structure)

### Step 1 — PDF extraction (no LLM)
New module `agents/pdf_extractor.py`:
- Walk `X:\DivisionOnline\FinalesProducto`
- For each game folder, locate the best description PDF using the rules above
- Extract text via `pypdf` or `pdfplumber` (add to `requirements.txt`)
- Write `data/pdf_extracts/<market>__<game>.json` with `{market, category, game_name, pdf_path, language, text}`
- Skip games already enriched in `output/games_enriched.csv` (check by base_key — can resolve via market_names.xlsx)

### Step 2 — Sub-agent classification (same conservative throttle as Session 5)
- 8 games per batch, 3 parallel per wave
- Each subagent receives: theme + feature system prompts, full taxonomy v2.3 (or v2.4 if mechanics confirmed first), N inlined PDF extracts, and the **Description extraction rule**.
- Output schema **extends Session 5's classified JSON with a new `description` field** — see schema below.
- Key difference from Session 5: PDF text is in **English (preferred) or Spanish**, often more polished/commercial than internal PPTX prose. Confidence should generally be higher (0.85+) for PDF-sourced classifications since these are public-facing game descriptions.

### Description blurb extraction rule (NEW for Session 6)
For each game, the sub-agent must produce a single English-language `description` field — the marketing blurb / intro paragraph used for SEO surfacing.

- **Always in English** in the output, regardless of PDF source language.
- **Source priority** (matches PDF discovery): `_ENG` / `_EN` PDF first; if only `_ESP` / `_ES` is available, translate the first description paragraph to English faithfully.
- **Extract verbatim where possible**: when the source PDF is English, copy the **first descriptive paragraph** (the marketing blurb that sits at the top of the PDF, before mechanic detail / pay tables / certifications) **verbatim**. Do not paraphrase, do not embellish.
- **When translating from Spanish**: stay close to the source — translate, do not rewrite. Preserve game-specific proper nouns (game name, character names) exactly.
- **Length**: typically 1–4 sentences, matching the source. Do not pad or truncate beyond what the PDF provides.
- **If no description paragraph found**: emit `description=""` and add `"missing_description"` to the classification's `notes` field; do not invent text.

### Updated subagent output schema
```json
{
  "base_key": "...",
  "folder_game_name": "...",
  "folder_category": "...",
  "pdf_found": true,
  "pdf_source_language": "EN" | "ES" | "BZL",
  "description": "First descriptive paragraph from the PDF, in English. Verbatim if source was English; faithfully translated if source was Spanish.",
  "themes": ["..."],
  "theme_confidence": 0.90,
  "theme_reasoning": "one sentence",
  "features": ["..."],
  "unknown_features": [],
  "feature_confidence": 0.85,
  "feature_reasoning": "one sentence",
  "notes": []
}
```

### Step 3 — Consolidation
Merge new classified JSONs into the existing `data/classified/` directory, then re-run:
- `python main.py localise` (idempotent — re-applies localisation/AM enrichment)
- `python main.py consolidate`
- `python generate_market_xlsx.py` (refreshes `themes_features_by_market.xlsx` with the new coverage)
- `python generate_report.py` (HTML)

**Code changes required for the new Description column:**
- `agents/consolidator.py` — add `description` to `OUTPUT_COLUMNS` and to `build_row()` (passes through from classified dict).
- `generate_market_xlsx.py` — add `Description` column to each market sheet (5 columns total: GameName, Category, Themes, Features, Description). Populate from enriched CSV by base_key.
- Backfill consideration: the 62 games already classified in Session 5 will not have `description` populated. They came from PPTX, not PDF. Either (a) leave them blank, (b) re-run them through the PDF pipeline if their PDFs exist on the share, or (c) generate a description from the PPTX slide text as a fallback. **Recommend (b)** — most of the 62 will have PDFs in FinalesProducto and the PDF blurb will be cleaner than PPTX prose.

## Pre-flight checklist (do these first in Session 6)

1. **Confirm mechanics review** (`output/missing_mechanics_review.xlsx`) is back from Product. Apply confirmed additions → bump taxonomy to v2.4 before classifying, so PDF-derived data uses the latest controlled vocabulary.
2. **Verify network share access**: `ls "X:/DivisionOnline/FinalesProducto"` — if not accessible, halt.
3. **Coverage gap math**: count games per market sheet currently empty in `themes_features_by_market.xlsx` to size the batch plan.

## Estimated scope

Roughly 440 rows × ~4k tokens/game = ~1.8M tokens in worst case. With the 8-games × 3-parallel × multi-wave pattern: ~55 sub-agents in ~18 waves. Conservative estimate: 1.5–2.0M tokens session total. **Recommend splitting across two sessions** — one per major market chunk (e.g. SPAIN+PORTUGAL first, then .COM+others).

## Risk register

| Risk | Mitigation |
|---|---|
| Network share `X:` unavailable | Pre-flight check; halt if missing |
| Many games have no Descripcion PDF | Log to gap report; do not block other classifications |
| PDF text extraction fails (image-only PDFs) | Try pypdf → pdfplumber → flag for OCR fallback (out of scope) |
| GameName ↔ folder mismatch (Brazilian / accented names) | rapidfuzz threshold 85; manual override map for known exceptions |
| Token blowout on first wave | Run a calibration batch of 4 games × 1 subagent; measure before scaling |
| Confidence inflation from polished PDF prose | Spot-check 5 random outputs against the source PDF to validate the classifier isn't overfitting to marketing copy |

## Deliverables

- `data/pdf_extracts/*.json` (one per game)
- `data/classified/*.json` extended with PDF-sourced rows + new `description` field
- Refreshed `output/themes_features_by_market.xlsx` — **5 columns now: GameName, Category, Themes, Features, Description**
- `output/games_enriched.csv` — extended with `description` column
- `output/pdf_coverage_report.csv` — what was found, what was missing, language used, whether description was extracted verbatim or translated
- Updated `dev/projectlog.md` Session 6 entry
- Updated `dev/ref/stage4-summary.md` (or stage6-summary.md per convention)

## Files to create/modify

- NEW `agents/pdf_extractor.py`
- NEW subcommand `python main.py extract-pdfs --input "X:\DivisionOnline\FinalesProducto"` in `main.py`
- `requirements.txt` — add `pypdf` (or `pdfplumber`)
- Possibly extend the sub-agent dispatch helper to handle PDF inputs (text content rather than slide structure)
