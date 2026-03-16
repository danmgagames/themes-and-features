# Architecture Reference

## Pipeline phases

### Phase 1 — Extraction (no API calls)
- Tool: `python-pptx` + `rapidfuzz` + `openpyxl`
- Input: PPTX folder tree (`\CATEGORY\GAMENAME\[files]`)
- Output: one JSON per game in `data/raw_extracts/`
- File selection: prefer filename containing "Comercial"; fallback to first .pptx
- Market lookup: fuzzy match GAMENAME folder against `market_names.xlsx` `name` + `COMMERCIAL NAME`

### Phase 2 — Classification (Claude API, parallel)
- 3 subagents per game, run concurrently via asyncio.gather
- Max 10 concurrent games (30 concurrent API calls max)
- Model: claude-sonnet-4-5
- Resume logic: skip `data/classified/{base_key}.json` if already exists
- Log: `data/classifier_log.jsonl`

**Theme classifier:** slide texts → SEO theme tags (English)
**Feature classifier:** slide texts → SEO feature tags + unknown_features list
**Localisation resolver:** mostly deterministic lookup; Claude only for 0.50–0.74 confidence matches

### Phase 3 — Consolidation + Output
- Merge 3 subagent outputs per game
- Flag if any confidence < 0.75, pptx_found=False, or unknown_features non-empty
- Output: `games_enriched.csv`, `review_flagged.csv`, `unknown_features_report.csv`
- Review loop: human edits `review_flagged.csv` → `main.py merge-review`

## Key data facts
- 700 rows in market_names.xlsx → 357 distinct game families
- 8 markets: SPAIN (311), PORTUGAL (103), .COM (79), NETHERLANDS (73), ITALY (71), COLOMBIA (55), CANADA (5), SWEDEN (3)
- 225 games are Spain-only (no other market variant)
- 19 deactivated games (skip by default, `--include-deactivated` flag to include)
- Game family grouping: strip suffix `(NoIp|Es|Pt|It|Co|Nl|Ca|Se)$` from tablename
- Spain entry = canonical / source-of-truth for each family
- Canada (Ca) + Sweden (Se) variants attach celebrity IPs (detect by commercial name prefix diff)

## PPTX structure (observed in sample)
- Slide 1: title (game name + category)
- Slide 2: "CATEGORIAS PRODUCTO" — primary source (mixed themes + features as bullets)
- Slide 3: "ARGUMENTOS DE VENTA" — secondary source (selling points, confirms features)
- No notes slides used
- Shape names are Spanish ("CuadroTexto", "Imagen") — not reliable for classification
- Themes and features are NOT structurally separated in slide 2 — Claude must classify them
- DEVELOPMENT section on slide 2 = internal dev notes, skip
- Disclaimer lines start with `*` — skip
- Standalone numbers (1,2,3,4) = layout artefacts — skip

## Output schema
See CLAUDE.md "Output schema" section for full column list.
Key: pipe-separated (|) multi-value fields; UTF-8-BOM encoding for Excel compatibility.

## Confidence thresholds
| Signal | Flag threshold |
|--------|---------------|
| Theme classifier | < 0.75 |
| Feature classifier | < 0.75 |
| Localisation fuzzy match | < 0.75 |
| No PPTX found | always flag |
| No market DB match | always flag |
| unknown_features non-empty | always flag |
