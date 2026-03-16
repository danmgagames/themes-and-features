# Stage 1 Summary — Extraction

## Folder structure (actual vs planned)

**Planned:** `CATEGORY/GAMENAME/[files]`
**Actual:** Varies by category:
- `MegaWays/NNNN_GameName/` (2 levels)
- `Slots3/Slots3/NNNN_GameName/` (3 levels, repeated subdir)
- `Slots5/Slots5/NNNN_GameName/` (3 levels, repeated subdir)
- Archive copies exist in `__Slots3/`, `__Slots5/` — 3 duplicates, resolved by overwrite

Game folders use numeric prefix: `0376_Take_The_Money_Megaways`

## Extraction stats

| Metric | Count |
|--------|-------|
| Game folders found | 131 (128 unique) |
| PPTXs found | 121 |
| PPTXs not found | 10 |
| Comercial files selected | 53 |
| Non-Comercial fallback | 68 |
| Category slide detected | 51/53 Comercial |
| Sales/features slide detected | 54 |
| JSON files written | 128 |

## Games per category
- MegaWays: 11
- Slots3: 98
- Slots5: 26 (including 1 in __Slots5 archive)

## PPTX slide formats observed

### Format A — "Comercial" (53 games, main target)
- Slide 1: Title (game name + category)
- Slide 2: "VENTA – CATEGORIAS PRODUCTO" — theme/feature tags as bullets
- Slide 3: "ARGUMENTOS DE VENTA" — selling points, confirms features

### Format B — Newer "Comercial" (8 games)
- Slide 2: "TEMÁTICAS" or "HISTORIA"
- Slide 3: "CARACTERISTICAS" with structured fields including "Categorías: ..."
- 6/8 detected after broadening header matching; 2 remaining use HISTORIA+CARACTERISTICAS

### Format C — Server/Design docs (68 games, fallback)
- No structured category/sales slides
- Contains raw game descriptions, mechanics details, character bios
- Classifier must work from unstructured text

## Missing data
- `market_names.xlsx` not in repo — market lookup entirely skipped
- `product_themes.xlsx` exists in POWERPOINTS/ with 60 games and pre-assigned themes (potential validation source)
- 10 games have empty folders (no PPTX): Poli_Diaz, Africa_Zero_GE, Mina_de_Oro_RE, Calico_Electronico, Boquerone_en_Venecia, Amarna_Miller_Cleopatra, Nika_OT, and 3 others

## Noise filtering applied
- Disclaimer lines (`*Gráficos...`)
- Standalone numbers (layout artefacts)
- "Internacional MGA", "Localización (Audios y textos)"
- DESARROLLO section content (internal dev notes)
