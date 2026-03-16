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
