# QA Checklist

## Session 1 — Extractor

- [ ] Verify Take The Money Megaways JSON: slide 2 = category, themes include Robos/Megaways/Aventuras
- [ ] Verify DESARROLLO section filtered from category slides
- [ ] Verify disclaimer lines (`*Gráficos...`) filtered
- [ ] Verify standalone numbers filtered from slide 3
- [ ] Verify "Comercial" PPTX preferred over other files in same folder
- [ ] Verify games with no PPTX produce JSON with `pptx_found: false`
- [ ] Verify no PPTX files from `old/` or `Aprobaciones/` subdirs are selected
- [ ] Spot-check 3 non-Comercial PPTXs — confirm text extraction is reasonable
- [ ] Confirm 128 JSON files in `data/raw_extracts/`
- [ ] Confirm extractor runs clean with no errors (`python main.py extract --input POWERPOINTS`)

## Session 2b — Classification Run

- [ ] Verify 128 classified JSONs exist in `data/classified/`
- [ ] Spot-check Take The Money Megaways: themes include Heist, Crime, Adventure, Classic, Movies & TV
- [ ] Spot-check Cleopatra Queen Fortune: themes include Egyptian, markets include SPAIN
- [ ] Verify celebrity games have "Celebrities" tag + person's name as separate tag
- [ ] Verify Chiquito games (Halloween, Navidad, Western, FistroGames) all have "Chiquito de la Calzada" tag
- [ ] Verify Megaways games all have "Megaways" feature tag
- [ ] Verify unknown_features arrays are populated (not empty) for games with non-standard mechanics
- [ ] Verify localisation fields (markets, es_commercial_name) populated for matched games
- [ ] Verify 5 Ca/Se celebrity IPs present in matched families (Charlie Riina, Lisa Mancini, etc.)
- [ ] Verify games with no PPTX have pptx_found=false and low confidence scores
- [ ] Confirm no classified JSON has empty themes array

## Session 3 — Consolidation + Output

### CSV output
- [x] `games_enriched.csv` opens in Excel without encoding issues (UTF-8-BOM)
- [x] Pipe-separated multi-value fields import cleanly
- [x] `review_flagged.csv` contains only flagged rows (91 of 128)
- [x] `review_flagged.csv` has `editor_notes` column at the end
- [x] Rows sorted: flagged first, then alphabetical by es_commercial_name
- [x] Category casing normalized (all uppercase)

### merge-review
- [x] Round-trip test: merge unedited review CSV → 91 merged, 0 still flagged
- [ ] Real-world test: edit a few rows in Excel, save, re-merge

### stats command
- [x] Counts match consolidate output
- [x] Top 10 themes/features display correctly
- [x] Category and market breakdowns accurate

### unknown features report
- [x] 51 features aggregated with counts and example games
- [x] suggested_standard_tag filled for all non-skipped entries
- [x] 6 new tags + 35 aliases added to seo_taxonomy.json
- [x] JSON validates after edits

### run-all command
- [ ] Not tested end-to-end (requires PPTX folder + classify phase)

### Pending human review
- [ ] Review `output/review_flagged.csv` (91 rows)
- [ ] Run `python main.py merge-review --review output/review_flagged.csv`
- [ ] Re-run `python main.py stats` to verify final numbers
