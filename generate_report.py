"""Generate an HTML report from games_enriched.csv for team review."""

import csv
from collections import Counter
from pathlib import Path

INPUT = Path('output/games_enriched.csv')
OUTPUT = Path('output/enrichment_report.html')


def load_data():
    with open(INPUT, 'r', encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))


def count_pipe_field(rows, field):
    counter = Counter()
    for r in rows:
        for val in r[field].split('|'):
            val = val.strip()
            if val:
                counter[val] += 1
    return counter


def bar_html(label, count, max_count, color):
    pct = (count / max_count * 100) if max_count else 0
    return f'''<div class="bar-row">
  <span class="bar-label">{label}</span>
  <div class="bar-track"><div class="bar-fill" style="width:{pct:.1f}%;background:{color}"></div></div>
  <span class="bar-count">{count}</span>
</div>'''


def section(title_en, title_es, counter, color, limit=None):
    items = counter.most_common(limit)
    if not items:
        return ''
    max_val = items[0][1]
    bars = '\n'.join(bar_html(label, count, max_val, color) for label, count in items)
    return f'''<div class="section">
  <h2 data-en="{title_en}" data-es="{title_es}">{title_en}</h2>
  {bars}
</div>'''


def summary_card(label_en, label_es, value, sub_en='', sub_es=''):
    sub_html = ''
    if sub_en:
        sub_html = f'<div class="card-sub" data-en="{sub_en}" data-es="{sub_es}">{sub_en}</div>'
    return f'''<div class="card">
  <div class="card-value">{value}</div>
  <div class="card-label" data-en="{label_en}" data-es="{label_es}">{label_en}</div>
  {sub_html}
</div>'''


def generate():
    rows = load_data()
    total = len(rows)

    themes = count_pipe_field(rows, 'themes')
    features = count_pipe_field(rows, 'features')
    categories = count_pipe_field(rows, 'category')
    markets = count_pipe_field(rows, 'markets')

    pptx_found = sum(1 for r in rows if r['pptx_found'] == 'True')
    reviewed = sum(1 for r in rows if r['review_reason'] == 'human_reviewed')

    # Separate SLOTS3-default features for clarity
    slots3_defaults = {'Mini-Games', 'Bonos Superiores', 'Dual-Screen Layout'}
    features_core = Counter({k: v for k, v in features.items() if k not in slots3_defaults})
    features_slots3 = Counter({k: v for k, v in features.items() if k in slots3_defaults})

    slots3_count = categories.get("SLOTS3", 0)

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Game Enrichment Report — MGA Pipeline</title>
<style>
  :root {{
    --bg: #0f1117;
    --surface: #1a1d27;
    --border: #2a2d3a;
    --text: #e4e4e7;
    --muted: #9ca3af;
    --accent: #6366f1;
  }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: var(--bg);
    color: var(--text);
    padding: 2rem;
    max-width: 1100px;
    margin: 0 auto;
  }}
  h1 {{
    font-size: 1.75rem;
    font-weight: 700;
    margin-bottom: 0.25rem;
  }}
  .header-row {{
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 0.25rem;
  }}
  .subtitle {{
    color: var(--muted);
    font-size: 0.95rem;
    margin-bottom: 2rem;
  }}
  .lang-toggle {{
    display: flex;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    overflow: hidden;
    flex-shrink: 0;
  }}
  .lang-btn {{
    padding: 0.4rem 0.9rem;
    font-size: 0.8rem;
    font-weight: 600;
    border: none;
    background: transparent;
    color: var(--muted);
    cursor: pointer;
    transition: all 0.2s;
  }}
  .lang-btn.active {{
    background: var(--accent);
    color: white;
  }}
  .lang-btn:hover:not(.active) {{
    color: var(--text);
  }}
  .cards {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 1rem;
    margin-bottom: 2.5rem;
  }}
  .card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 1.25rem 1rem;
    text-align: center;
  }}
  .card-value {{
    font-size: 2rem;
    font-weight: 700;
    color: var(--accent);
  }}
  .card-label {{
    font-size: 0.8rem;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-top: 0.25rem;
  }}
  .card-sub {{
    font-size: 0.75rem;
    color: var(--muted);
    margin-top: 0.25rem;
  }}
  .columns {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 2rem;
    margin-bottom: 2rem;
  }}
  @media (max-width: 768px) {{
    .columns {{ grid-template-columns: 1fr; }}
  }}
  .section {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 1.5rem;
    margin-bottom: 1.5rem;
  }}
  .section h2 {{
    font-size: 1rem;
    font-weight: 600;
    margin-bottom: 1rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--muted);
  }}
  .bar-row {{
    display: flex;
    align-items: center;
    margin-bottom: 0.5rem;
    gap: 0.75rem;
  }}
  .bar-label {{
    width: 180px;
    min-width: 180px;
    font-size: 0.85rem;
    text-align: right;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }}
  .bar-track {{
    flex: 1;
    height: 22px;
    background: var(--bg);
    border-radius: 4px;
    overflow: hidden;
  }}
  .bar-fill {{
    height: 100%;
    border-radius: 4px;
    transition: width 0.6s ease;
  }}
  .bar-count {{
    width: 40px;
    min-width: 40px;
    font-size: 0.85rem;
    font-weight: 600;
    text-align: right;
    color: var(--muted);
  }}
  .note {{
    font-size: 0.8rem;
    color: var(--muted);
    font-style: italic;
    margin-top: 0.75rem;
  }}
  .full-width {{
    grid-column: 1 / -1;
  }}
  footer {{
    text-align: center;
    color: var(--muted);
    font-size: 0.75rem;
    margin-top: 2rem;
    padding-top: 1rem;
    border-top: 1px solid var(--border);
  }}
</style>
</head>
<body>

<div class="header-row">
  <h1 data-en="Game Enrichment Report" data-es="Informe de Enriquecimiento de Juegos">Game Enrichment Report</h1>
  <div class="lang-toggle">
    <button class="lang-btn active" onclick="setLang('en')">EN</button>
    <button class="lang-btn" onclick="setLang('es')">ES</button>
  </div>
</div>
<p class="subtitle"
   data-en="MGA Pipeline &mdash; {total} games classified &middot; Generated from games_enriched.csv"
   data-es="Pipeline MGA &mdash; {total} juegos clasificados &middot; Generado desde games_enriched.csv">
  MGA Pipeline &mdash; {total} games classified &middot; Generated from games_enriched.csv
</p>

<div class="cards">
  {summary_card("Total Games", "Total Juegos", total)}
  {summary_card("PPTX Found", "PPTX Encontrados", pptx_found,
                 f"{total - pptx_found} missing", f"{total - pptx_found} sin encontrar")}
  {summary_card("Human Reviewed", "Revisados", reviewed)}
  {summary_card("Unique Themes", "Temas Únicos", len(themes))}
  {summary_card("Unique Features", "Features Únicos", len(features))}
  {summary_card("Markets", "Mercados", len(markets))}
</div>

<div class="columns">
  {section("Games by Category", "Juegos por Categoría", categories, "#6366f1")}
  {section("Games by Market", "Juegos por Mercado", markets, "#8b5cf6")}
</div>

{section("All Themes (by frequency)", "Todos los Temas (por frecuencia)", themes, "#10b981")}

{section("Features — Core Mechanics", "Features — Mecánicas Principales", features_core, "#f59e0b")}

{section("Features — SLOTS3 Defaults (auto-applied)", "Features — SLOTS3 por Defecto (auto-aplicados)", features_slots3, "#6366f1")}
<p class="note" style="margin-top:-1rem;margin-bottom:2rem;"
   data-en="SLOTS3 default features (Mini-Games, Bonos Superiores, Dual-Screen Layout) are automatically added to all {slots3_count} SLOTS3 games."
   data-es="Los features por defecto de SLOTS3 (Mini-Games, Bonos Superiores, Dual-Screen Layout) se añaden automáticamente a los {slots3_count} juegos SLOTS3.">
  SLOTS3 default features (Mini-Games, Bonos Superiores, Dual-Screen Layout) are automatically added to all {slots3_count} SLOTS3 games.
</p>

<footer
   data-en="MGA Game Enrichment Pipeline &middot; Data from {total} classified games"
   data-es="Pipeline de Enriquecimiento MGA &middot; Datos de {total} juegos clasificados">
  MGA Game Enrichment Pipeline &middot; Data from {total} classified games
</footer>

<script>
function setLang(lang) {{
  document.querySelectorAll('[data-en][data-es]').forEach(function(el) {{
    el.innerHTML = el.getAttribute('data-' + lang);
  }});
  document.querySelectorAll('.lang-btn').forEach(function(btn) {{
    btn.classList.toggle('active', btn.textContent === lang.toUpperCase());
  }});
  document.documentElement.lang = lang;
}}
</script>

</body>
</html>'''

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(html, encoding='utf-8')
    print(f'Report written to {OUTPUT}')


if __name__ == '__main__':
    generate()
