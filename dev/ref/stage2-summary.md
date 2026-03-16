# Stage 2 Summary — Classification Run

## Execution method
- 13 Claude Code sub-agents, each processing a batch of 10 games (last batch: 3)
- 3 waves: wave 1 (batches 1-4), wave 2 (batches 5-8), wave 3 (batches 9-13)
- All sub-agents ran in background, 4-5 parallel per wave
- Localisation resolver ran once in main context after all sub-agents completed
- Total duration: ~20 minutes wall-clock

## Results

### Classification coverage
- 128 games classified (100% of raw extracts)
- 89 matched to market_names.xlsx families (69%)
- 39 unmatched — these are games present in PPTX folders but not in the market DB

### Confidence distribution
| Metric | Count | Notes |
|--------|-------|-------|
| Theme confidence >= 0.75 | 105 | Good coverage |
| Theme confidence < 0.75 | 23 | Design-only PPTXs, name-inferred |
| Feature confidence >= 0.75 | 71 | |
| Feature confidence < 0.75 | 57 | Slots3 design PPTXs lack mechanic detail |
| No PPTX found | 7 | Games with pptx_found=false |

### Celebrity detections
**From Ca/Se market variants (localisation resolver):**
- Charlie Riina → Alchemist Riches
- Lisa Mancini → Astral Spin
- Joshua Guvi → Explosive Bandit
- Ron Josol → FarWestMania Megaways
- Taya Valkyrie → GoldMine Megaways

**From game names (classifier):**
- Chiquito de la Calzada (multiple games)
- Samantha Fox, Canales Rivera, Cañita Brava, Makoke
- Mario Vaquerizo, El Sevilla, Juan Muñoz
- El Dioni, Maria Lapiedra, Yola Berrocal
- Cecilia Sopeña, Barragán, El Koala (musician)
- David Meca, Amarna Miller, Rebeca Pous
- Elsa Anka, Sonia Monroy, Sofia Cristo
- Aurah Ruiz, Mireia Lalaguna, Gemma Mengual
- Nika (OT), Manolo El del Bombo

### Unknown features (51 unique)
These are Spanish bar-machine mechanics and game-specific features not in the SEO taxonomy.
Key clusters:
- **Bar-machine classics:** Avances, Retenciones, Paralo, Giro Ganador, Sube tu Premio, Suma Premio
- **Minigames:** Trilero, Pinball, Ruleta, Barcos, Piramide, Carreras
- **Slots5 specific:** MultiRatio/MultiVolatility, Wild Night, Twin Spin, Money Symbols per line
- **Misc:** Deal or No Deal mechanic, DiscoverPrize, Risk/Gamble Free Spins

### Match methods (localisation)
| Method | Count |
|--------|-------|
| fuzzy_commercial | 50 |
| fuzzy_base_key | 25 |
| exact_base_key | 8 |
| exact_commercial | 6 |
| none (unmatched) | 39 |

## Observations
1. Slots3 games consistently have lower feature confidence because most PPTXs are design/bocetos docs, not commercial decks. The actual mechanics are inherited from base game engines and not explicitly described.
2. The high unmatched count (39) is expected — many PPTX folders contain games in development or internal test builds not yet in the market DB.
3. The unknown features list is dominated by traditional Spanish bar-machine mechanics (Avances, Retenciones, Paralo) which are not relevant for SEO taxonomy but should be reviewed for potential inclusion.
