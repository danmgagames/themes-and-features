# Taxonomy Decisions

## Theme taxonomy source
Derived from Pragmatic Play competitor data (580 PT-market slots).
Pragmatic's labels are market-standard — casino aggregators and SEO tools use these terms.
Adopted as seed; MGA-specific additions noted below.

## Key decisions made

### Split broad categories for SEO surface area
- "Sport Celebrities" → split into `Sport` + `Celebrities` (separate tags)
- Rationale: catches searches for both independently

### Celebrity / IP tagging — stack all three
For celebrity-attached games (e.g. Abigail Ratchford, Andy Soucek, Paulo Futre):
1. `Celebrities` (generic tag)
2. Celebrity's full name (e.g. `Abigail Ratchford`) — for name-search SEO
3. Relevant genre/sport tag (e.g. `Sport`, `Racing`, `Boxing`)
- Rationale: maximises SEO surface area across all search intents

### Movies & TV — dual tagging
- Apply `Movies & TV` tag AND the specific genre tag (e.g. `Heist`, `Western`)
- Rationale: catches both "movies slot" and "heist slot" searches
- Pragmatic Play don't do IP games so this tag doesn't exist in their taxonomy — MGA addition

### IP / Licensed — dropped
- Not used as a theme tag (B2B language, not end-user SEO)

### MGA-specific additions to Pragmatic taxonomy
| Tag | Reason |
|-----|--------|
| Movies & TV | MGA makes IP/licensed games; Pragmatic doesn't |
| Sport | Split from "Sport Celebrities" |
| Celebrities | Split from "Sport Celebrities" |
| Heist | Sub-genre of Adventure; common in MGA games |
| Crime | Sub-genre of Adventure |

## Feature taxonomy approach
Two-pass strategy:
1. Session 2 extraction pass surfaces all MGA mechanic terms from PPTXs
2. `unknown_features_report.csv` generated in Session 3 lists all unmapped terms
3. Human reviews report and extends `seo_taxonomy.json` features section
4. Re-run classify pass to apply new tags (resume logic skips already-classified)

## Spanish → English aliases
Full mapping in `config/seo_taxonomy.json` under `spanish_aliases`.
Key mappings:
- "Robos" → Heist, Crime, Adventure
- "Películas y Televisión" → Movies & TV
- "Compra Free Spins" / "Opción de compra" → Buy Feature, Buy Free Spins
- "Megaways" → Megaways (unchanged)
- "Estilo clásico" → Classic
- "DESARROLLO" section → skip entirely (internal dev notes)

## Multi-value convention
Games typically have 2–6 themes and 2–8 features.
Classifier is instructed to assign ALL applicable tags, not just the most prominent.
Output fields are pipe-separated (|) to avoid CSV parsing issues with commas.
