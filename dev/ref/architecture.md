# Architecture Reference

## Pipeline phases

### Phase 1 — Extraction (no API calls)
- Tool: `python-pptx` + `rapidfuzz` + `openpyxl`
- Input: PPTX folder tree (`\CATEGORY\GAMENAME\[files]`)
- Output: one JSON per game in `data/raw_extracts/`
- File selection: prefer filename containing "Comercial"; fallback to first .pptx
- Market lookup: fuzzy match GAMENAME folder against `market_names.xlsx` `name` + `COMMERCIAL NAME`

### Phase 2 — Classification (Claude Code sub-agents, no external API)
- **Approach changed:** instead of Claude API calls, classification runs via Claude Code
  sub-agents (Agent tool), each processing a batch of 10 games
- 13 sub-agents total (128 games / 10 per batch, last batch gets 8)
- Each sub-agent reads the taxonomy + its 10 raw extract JSONs, classifies themes &
  features, and writes 10 classified JSONs to `data/classified/`
- Sub-agents run 3–4 in parallel (background) to stay within context limits
- Localisation resolution remains deterministic (no LLM needed) — runs in main context
- **No API key or API credits required** — uses Claude Max plan tokens only
- Resume logic: skip `data/classified/{base_key}.json` if already exists

**Theme classification:** slide texts → SEO theme tags (English), using taxonomy + spanish_aliases
**Feature classification:** slide texts → SEO feature tags + unknown_features list
**Localisation resolver:** deterministic lookup against market_names.xlsx game families;
  celebrity IP detection from Ca/Se variant name prefixes

### Phase 3 — Consolidation + Output
- Merge classified outputs per game
- Flag if any confidence < 0.75, pptx_found=False, or unknown_features non-empty
- Output: `games_enriched.csv`, `review_flagged.csv`, `unknown_features_report.csv`
- Review loop: human edits `review_flagged.csv` → `main.py merge-review`

## Sub-agent batch structure (Phase 2)

Each classification sub-agent receives:
1. The SEO taxonomy (config/seo_taxonomy.json) — themes, features, spanish_aliases
2. A list of 10 raw extract JSON file paths to process
3. Instructions to classify each game and write output to data/classified/

Sub-agent output per game:
```json
{
  "base_key": "...",
  "themes": ["Tag1", "Tag2"],
  "theme_confidence": 0.85,
  "theme_reasoning": "...",
  "features": ["Tag1", "Tag2"],
  "unknown_features": ["..."],
  "feature_confidence": 0.85,
  "feature_reasoning": "..."
}
```

Localisation fields (markets, celebrity_names, es_commercial_name) are added
separately by the localisation resolver in the main context after all sub-agents complete.

## Key data facts
- 700 rows in market_names.xlsx → 357 distinct game families (341 active)
- 8 markets: SPAIN (311), PORTUGAL (103), .COM (79), NETHERLANDS (73), ITALY (71), COLOMBIA (55), CANADA (5), SWEDEN (3)
- 225 games are Spain-only (no other market variant)
- 19 deactivated games (skip by default, `--include-deactivated` flag to include)
- Game family grouping: strip suffix `(NoIp|Es|Pt|It|Co|Nl|Ca|Se)$` from tablename
- Spain entry = canonical / source-of-truth for each family
- Canada (Ca) + Sweden (Se) variants attach celebrity IPs (detect by commercial name prefix diff)

## PPTX structure (observed across 121 files)

### Format A — "Comercial" standard (45 games)
- Slide 2: "VENTA – CATEGORIAS PRODUCTO" — theme/feature tags as bullets
- Slide 3: "ARGUMENTOS DE VENTA" — selling points

### Format B — "Comercial" newer (8 games)
- Slide 2: "TEMÁTICAS" or "HISTORIA"
- Slide 3: "CARACTERISTICAS" — structured fields incl "Categorías: ..."

### Format C — Server/Design fallback (68 games)
- No structured category slides; raw game text only

### Common noise patterns (filtered by extractor)
- DESARROLLO section = internal dev notes, skip
- Disclaimer lines start with `*` — skip
- Standalone numbers (1,2,3,4) = layout artefacts — skip
- "Internacional MGA", "Localización (Audios y textos)" = distribution notes, skip

## Actual folder structure
`CATEGORY/[CATEGORY/]NNNN_GameName/[files]`
- MegaWays: 2 levels deep
- Slots3, Slots5: 3 levels deep (repeated category subdir)
- Game folders have numeric prefix: `0376_Take_The_Money_Megaways`

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
