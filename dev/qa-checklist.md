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
- [x] Real-world test: human-edited review CSV merged — 91 merged, 0 still flagged

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
- [x] Review `output/review_flagged.csv` (91 rows)
- [x] Run `python main.py merge-review --review output/review_flagged.csv`
- [x] Re-run `python main.py stats` to verify final numbers

## Session 4 — Human review feedback + HTML report

### Feature normalization
- [x] "Free Spins" renamed to "Free Rounds" in enriched CSV (no standalone "Free Spins" remains)
- [x] "Progressive Free Spins" and "Buy Free Spins" unchanged (correct — only standalone renamed)
- [x] "Bonus Round" removed where "Bonus Game" coexists (1 game with only "Bonus Round" correctly kept)
- [x] All 91 SLOTS3 games have Mini-Games, Bonos Superiores, Dual-Screen Layout
- [x] `seo_taxonomy.json` v2.1 validates as JSON

### HTML report
- [x] `generate_report.py` runs without errors
- [x] `output/enrichment_report.html` opens in browser
- [x] EN/ES toggle switches all UI text
- [x] Theme/feature tag names remain in English in both languages
- [ ] Spot-check: bar chart widths proportional to counts

## Session 6a — PDF enrichment + PP candidate side-channel

### PDF extraction
- [ ] Spot-check 3 PDF extracts in `data/pdf_extracts/` — text reasonable, no garbled mojibake
- [ ] Verify the 4 PDF discovery rules cover SLOTS5 / BINGO / RULETA conventions (Marketing Assets/06., Gamesheets/, descripcion/, fallback)
- [ ] Verify `--overwrite` flag forces re-extraction; default skip-when-enriched is idempotent
- [ ] Verify 19 truly-orphaned folders are 3rd-party / external-IP games not in market_names.xlsx (confirm by reading 5 samples in `output/pdf_coverage_survey.csv`)

### Sub-agent classification (84 new games)
- [ ] Spot-check 5 random `data/classified/<base_key>.json` against the source PDF — themes/features plausible, description verbatim or cleanly translated
- [ ] Confirm no SLOTS5 PDF mentions Advance/Hold without `Nudge & Hold` tagged
- [ ] Confirm no celebrity-named game lacks `Celebrities` + the person's name as themes
- [ ] Spot-check `description` field for hyphen-rejoin (e.g. "Ri-quezas" → "Riquezas") and removed column-header artefacts ("CASINO SLOTS", "MAIN GAME")

### PP candidate side-channel (the side-channel must NOT leak into features)
- [ ] Open `output/pp_mechanic_candidates.csv` — confirm 4 rows: 3× Increasing Wilds, 1× Mystery Expanding Symbol
- [ ] For each of the 4 candidate games, open the PDF on the X drive and confirm the evidence quote is verbatim from the source
- [ ] grep `data/classified/*.json` for `Hyperplay|Powernudge|Super Scatter` — must find zero hits anywhere
- [ ] grep for `Increasing Wilds|Mystery Expanding Symbol` — only inside `pp_candidate_mechanics` arrays, never in `features` or `unknown_features`
- [ ] Confirm Powernudge-style language (if any in 6a games) was tagged as `Nudge & Hold` (not flagged as PP candidate)

### Cross-market deliverable
- [ ] Open the latest `themes_features_by_market.xlsx` (or `.LATEST.xlsx` if Excel was open during 6a). Confirm 5 columns per sheet: GameName, Category, Themes, Features, Description
- [ ] Confirm no regression on the 69 Session-5 rows (themes/features unchanged where present)
- [ ] Confirm the 159 newly enriched rows have populated Themes + Features
- [ ] Description column populated only for the 84 PDF-sourced games; the 62 Session-5 games still have blank Description (pending 6c backfill)

### Validation gate
- [x] All 7 checks in `dev/validate_session6a.py` passed
- [ ] Re-run `python dev/validate_session6a.py` after any manual touchups to confirm clean state

### Pending tracker
- [ ] Investigate `localisation_resolver.match_extract_to_family` no-match for 52/200 (SPAIN/.COM cname masking quirk). Decide: (a) fix by adding the same per-market lookup the PDF extractor uses, or (b) leave alone since cross-market deliverable still works.
- [ ] Once Product greenlights any of the 4 PP candidate mechanics → bump taxonomy to v2.4, dispatch a tiny re-classification wave for just the 4 affected games (Diamond Mine, Explosive Bandit 2, Explosive Wizard Cat, Dragons Double Pot).

## Session 6b — PDF enrichment SLOTS3 tail

### Sub-agent classification (54 new games — 50 SLOTS3 + 4 BINGO)
- [ ] Spot-check 5 random `data/classified/S3*.json` and `BingoGeneralCounters*.json` (newest mtime) — themes/features plausible, description verbatim or cleanly translated
- [ ] Confirm at least one Spanish-source SLOTS3 game has a faithful English translation in its description (e.g. `S3AndyLucasCountersGlobal` was flagged `pdf_lang=ES`)
- [ ] Verify celebrity-named SLOTS3 games (Andy & Lucas, Aramis Fuster, Pocholo, Yola Berrocal, Cecilia, Maria La Piedra, Ismael Beiro, Eugenio, Dioni, Flash Gordon) have `Celebrities` + the person's name as themes
- [ ] Verify all 50 SLOTS3 games show `Mini-Games`, `Bonos Superiores`, `Dual-Screen Layout` in `output/games_enriched.csv` after consolidate (auto-injected by `normalize_features`)

### Validation gate
- [x] Re-run `python dev/validate_session6a.py` — all 7 checks passed for 138 PDF-sourced JSONs

### Cross-market deliverable
- [ ] Open `output/themes_features_by_market.xlsx` SPAIN sheet — 127 of 232 rows now enriched (54.7% coverage, up from 35.8%)
- [ ] Confirm none of the 50 SLOTS3 games regressed (compare against pre-6b state if needed)

### PP candidates (no new hits expected from SLOTS3/BINGO)
- [x] Confirmed: 0 new PP candidates from 6b. Total side-channel still 4 hits, all from 6a.

## Session 6c — PDF Description backfill for 47 Session-5 games

### Sub-agent classification (47 backfills — 9 MEGAWAYS + 38 SLOTS3)
- [ ] Spot-check 5 random `data/classified_6c/<base_key>.json` — themes/features plausible, description verbatim (EN PDFs) or cleanly translated (ES PDFs)
- [ ] Confirm celebrity-named SLOTS3 backfills (Canales Rivera, Chiquito, El Sevilla, Juan Muñoz, Makoke, Mario Vaquerizo, Mask Singer, Pasapalabra, RF Burlesque, Samantha Fox, El Cartel) carry `Celebrities` + the person's name in themes (in either Session 5 or 6c — even if Session 5 stays authoritative, 6c output should agree)
- [ ] Confirm at least one SLOTS3 backfill with `pdf_source_language: "ES"` has a faithful English translation in its `description`

### Merge / diff post-processor
- [ ] Open `data/classified/MegawaysGeneralCountersChefDelights.json` — confirm Session 5 themes (`Food`, `Movies & TV`) preserved AND new keys present: `description`, `pdf_source_language`, `pdf_found`, `pp_candidate_mechanics`
- [ ] Confirm `data/classified/` has 200 JSONs and 185 of them carry both `description` and `pdf_source_language`
- [ ] Confirm `data/classified_6c/` has exactly 47 JSONs (preserved as backup of sub-agent output)

### backfill_diffs.csv (the human-review surface — Session 5 stays authoritative)
- [ ] Open `output/backfill_diffs.csv` — confirm 34 rows (22 themes, 12 features), each with both confidences ≥ 0.85
- [ ] Spot-check 3 themes-kind rows — confirm `only_in_s6c` adds make sense from PDF prose (not hallucinations)
- [ ] Spot-check 3 features-kind rows — confirm dominant adds are `Bonus Game` / `Nudge & Hold` (PDF tech-table convention)
- [ ] Decide whether any of the 34 disagreements should override Session 5; document the call in this checklist

### PP candidates (no new hits expected from these 47 games)
- [x] Confirmed: 0 new PP candidates from 6c. Total side-channel still 4 hits, all from 6a.

### Cross-market deliverable
- [ ] Open `output/themes_features_by_market.xlsx` SPAIN sheet — Description column populated for all 127 enriched rows (was 83 pre-6c; +44 from 6c)
- [ ] Confirm no themes/features regression on the 47 backfilled games (Session 5 stays authoritative on the merged JSON)

### Validation gate
- [x] Re-run `python dev/validate_session6a.py` — all 7 checks passed for 185 PDF-sourced JSONs

## Session 6d — Per-market celebrity-name validation in market xlsx

### Generator + audit log
- [x] `python generate_market_xlsx.py` runs; console prints "Celebrity pool: 46 tags"
- [x] `output/celebrity_corrections.csv` written with 60 rows: 29 removals + 2 additions + 29 umbrella drops
- [x] No taxonomy umbrella key (e.g. `Nature & Animals`, `Fantasy & Mythology`) appears in the removed-tags list

### SPAIN spot-checks
- [ ] "Lejano Oeste Mania Megaways" themes — `Ron Josol` and `Celebrities` both gone (Canada-IP bleed pruned)
- [ ] 6× Chiquito SPAIN rows (Halloween, Navidad, Western, Fistrogames, Medieval, Condemor) — `Chiquito de la Calzada` and `Celebrities` both gone (strict full-name policy intentionally trims truncated localisations)
- [ ] "Andy Y Lucas" — `Andy & Lucas` SURVIVES (conjunction normalization `& ↔ y` works)
- [ ] "Sonia Monroy En El Planeta Halloween" — gets `Sonia Monroy` + `Celebrities` added (swap-in: base_key has no celebrity, SPAIN-localised name introduces her)
- [ ] "Mario Vaquerizo Salvaje" / "Samantha Fox" / "Pasapalabra" / "Cañita Brava" / etc. — celebrity tag and umbrella both retained

### Other-market spot-checks
- [ ] PORTUGAL "Velho Oeste Mania Megaways" → `Ron Josol` and umbrella gone
- [ ] .COM "Jade Goddess" → `Aurah Ruiz` and umbrella gone (Spain-only celebrity)
- [ ] ITALY "Lo Stregone Megaways" → `Nacho Vidal` and umbrella gone
- [ ] NETHERLANDS "Milou Tamara Goudmijn Mania Megaways" → `Taya Valkyrie` and umbrella gone

### Audit-log spot-check
- [ ] Open `output/celebrity_corrections.csv` — sorted (sheet, base_key, action, tag); spot-check 3 `remove` rows against their GameName visually

### No regressions
- [x] `output/games_enriched.csv` mtime unchanged — consolidator was not re-run
- [ ] Re-run `python dev/validate_session6a.py` — still passes (classified JSONs untouched)
- [ ] Per-sheet enrichment Coverage % matches pre-6d (no row drops)
