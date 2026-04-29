"""
mga.games bulk scraper.

Phase A — Discovery:
  Visit /games on each of 6 markets (selected via the market chooser modal),
  scroll/wait for tiles, collect (market, slug, displayed_name, category)
  for every tile. Output: dev/_scrape/catalog.csv.

Phase B — Per-game scrape:
  For each unique slug, visit /games/<slug>, parse the rendered DOM, extract:
    title, type, description, volatilidad, apuesta_min, apuesta_max,
    premio_max, related_slugs.
  Cache full HTML to dev/_scrape/games/<slug>.html (skipped on re-runs)
  Output: dev/_scrape/games.csv

Polite: 1.5s delay between page loads. Idempotent: cached HTML reused.
"""
import asyncio
import csv
import json
import re
import sys
from pathlib import Path

from playwright.async_api import async_playwright

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT = PROJECT_ROOT / 'dev' / '_scrape'
GAMES_HTML = OUT / 'games'
OUT.mkdir(parents=True, exist_ok=True)
GAMES_HTML.mkdir(parents=True, exist_ok=True)

# Market chooser labels (rendered Spanish) → AM-style market label
MARKET_LABELS = [
    ('España', 'SPAIN'),
    ('Portugal', 'PORTUGAL'),
    ('Colombia', 'COLOMBIA'),
    ('Italia', 'ITALY'),
    ('Países Bajos', 'NETHERLANDS'),
    ('Otros Mercados', '.COM'),
]

REQUEST_DELAY_S = 1.5
TILE_LOAD_WAIT_S = 4

USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/124.0 Safari/537.36 '
    'mga-themes-features-bot/1.0 (dnugent@mga.es internal cataloguing)'
)


PICK_MARKET_JS = """(label) => {
  // First try: click an element whose text is exactly the market label
  // (the home-page "Elige tu mercado" modal renders one of these per market).
  const candidates = document.querySelectorAll('button, a, div, li, span');
  for (const el of candidates) {
    const t = (el.innerText || '').trim();
    if (t === label) {
      el.click();
      return 'modal';
    }
  }
  // Second try: in-page MERCADO filter shows '<MARKET>(<count>)' — match by prefix.
  // The market filter labels on /games are uppercase: ESPAÑA, PORTUGAL,
  // COLOMBIA, OTROS MERCADOS, ITALIA, PAÍSES BAJOS.
  const upper = label.toUpperCase();
  const altMap = {
    'ESPAÑA':'ESPAÑA','PORTUGAL':'PORTUGAL','COLOMBIA':'COLOMBIA',
    'ITALIA':'ITALIA','PAÍSES BAJOS':'PAÍSES BAJOS',
    'OTROS MERCADOS':'OTROS MERCADOS',
  };
  const upperLabel = altMap[upper] || upper;
  for (const el of candidates) {
    const t = (el.innerText || '').trim();
    // Match exact filter chip like "PORTUGAL(55)" or "PORTUGAL (55)"
    const m = t.match(/^([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s]+?)\s*\(\d+\)$/);
    if (m && m[1].trim() === upperLabel) {
      el.click();
      return 'filter';
    }
  }
  // Third try: just the uppercase label without count (deselected chip
  // sometimes drops the count).
  for (const el of candidates) {
    const t = (el.innerText || '').trim();
    if (t === upperLabel) {
      el.click();
      return 'plain';
    }
  }
  return null;
}"""

ACCEPT_COOKIES_JS = """() => {
  for (const el of document.querySelectorAll('button, a')) {
    const t = (el.innerText || '').trim().toLowerCase();
    if (t === 'aceptar cookies' || t === 'aceptar' || t === 'accept all') {
      el.click();
      return true;
    }
  }
  return false;
}"""

EXTRACT_TILES_JS = r"""() => {
  const tiles = [];
  // mga.games game tiles are <a href="/games/<slug>"> wrappers
  document.querySelectorAll('a[href^="/games/"]').forEach(a => {
    const href = a.getAttribute('href') || '';
    const m = href.match(/^\/games\/([^/?#]+)\/?$/);
    if (!m) return;
    const slug = m[1];
    // Pull all text under this anchor — usually has name + category line
    const text = (a.innerText || '').trim();
    tiles.push({slug, href, text});
  });
  return tiles;
}"""

EXTRACT_GAME_FIELDS_JS = r"""() => {
  const out = {};
  out.title = document.title || '';
  out.body_text = (document.body ? document.body.innerText : '') || '';

  // Heuristic field extraction from "RESUMEN" block
  const txt = out.body_text;
  const m_type = txt.match(/Tipo de juego:\s*([^\n]+)/i);
  const m_bet = txt.match(/Apuesta:\s*([^\n]+)/i);
  const m_vol = txt.match(/Volatilidad:\s*([^\n]+)/i);
  const m_max = txt.match(/Premio m[aá]x\.?:\s*([^\n]+)/i);

  out.tipo = m_type ? m_type[1].trim() : '';
  out.apuesta = m_bet ? m_bet[1].trim() : '';
  out.volatilidad = m_vol ? m_vol[1].trim() : '';
  out.premio_max = m_max ? m_max[1].trim() : '';

  // Description: paragraphs of the main content area, before "RESUMEN"
  const idx = txt.indexOf('RESUMEN');
  let desc_block = idx > 0 ? txt.slice(0, idx) : txt.slice(0, 2000);
  // Drop nav and game name lines — keep paragraphs of >=80 chars
  const paras = desc_block.split('\n').map(s => s.trim())
    .filter(s => s.length >= 80);
  out.description = paras.join(' ').trim();

  // Related games (visible at bottom)
  const related = [];
  document.querySelectorAll('a[href^="/games/"]').forEach(a => {
    const href = a.getAttribute('href') || '';
    if (href === location.pathname || href === location.pathname + '/') return;
    const m = href.match(/^\/games\/([^/?#]+)\/?$/);
    if (!m) return;
    related.push(m[1]);
  });
  out.related = Array.from(new Set(related));

  return out;
}"""


async def accept_cookies(page):
    try:
        await page.evaluate(ACCEPT_COOKIES_JS)
        await page.wait_for_timeout(500)
    except Exception:
        pass


async def pick_market(page, label):
    """Try modal click, then in-page MERCADO filter chip click."""
    for attempt in range(4):
        method = await page.evaluate(PICK_MARKET_JS, label)
        if method:
            await page.wait_for_timeout(1500)
            return method
        # Try opening the MERCADO filter dropdown to expose the chips.
        try:
            await page.evaluate("""() => {
              for (const el of document.querySelectorAll('button, a, div')) {
                const t = (el.innerText || '').trim();
                if (t === 'MERCADO' || t.startsWith('MERCADO ') || t.startsWith('MERCADO ')) {
                  el.click();
                  return;
                }
              }
            }""")
        except Exception:
            pass
        await page.wait_for_timeout(800)
    return None


async def discover_market(page, market_label, market_key, is_first):
    """Always clear storage + cookies + visit home so the market modal
    reappears for each market."""
    print(f'\n[discover] {market_key}')
    try:
        await page.context.clear_cookies()
    except Exception:
        pass
    try:
        # Clear localStorage / sessionStorage; tolerate SecurityError when
        # called before any document is loaded.
        await page.evaluate(
            "() => { try { localStorage.clear(); sessionStorage.clear(); } catch(e) {} }"
        )
    except Exception:
        pass

    try:
        await page.goto('https://mga.games/', wait_until='domcontentloaded', timeout=45000)
    except Exception as e:
        print(f'  home goto warn: {e}')
    await page.wait_for_timeout(2500)
    await accept_cookies(page)
    picked = await pick_market(page, market_label)
    print(f'  home picked={picked}')

    try:
        await page.goto('https://mga.games/games', wait_until='domcontentloaded', timeout=45000)
    except Exception as e:
        print(f'  goto warn: {e}')
    await page.wait_for_timeout(TILE_LOAD_WAIT_S * 1000)
    await accept_cookies(page)

    # Scroll to bottom to ensure all tiles render (some Angular lists lazy-load)
    last_h = -1
    for _ in range(10):
        h = await page.evaluate('document.body.scrollHeight')
        if h == last_h:
            break
        last_h = h
        await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
        await page.wait_for_timeout(700)
    await page.evaluate('window.scrollTo(0, 0)')
    await page.wait_for_timeout(500)

    tiles = await page.evaluate(EXTRACT_TILES_JS)
    # Dedupe by slug, keep first text
    seen = {}
    for t in tiles:
        if t['slug'] not in seen:
            seen[t['slug']] = t
    tiles = list(seen.values())
    print(f'  tiles found: {len(tiles)}')
    out = []
    for t in tiles:
        # text typically: "<name>\n<type>\n<market_code>" plus extras
        lines = [l.strip() for l in (t.get('text') or '').split('\n') if l.strip()]
        # Drop obvious chrome
        chrome = {'Jugar', 'Ver más', 'Vídeo', 'PRÓXIMAMENTE'}
        lines = [l for l in lines if l not in chrome]
        name = lines[0] if lines else ''
        cat = lines[1] if len(lines) > 1 else ''
        out.append({
            'market': market_key,
            'slug': t['slug'],
            'displayed_name': name,
            'category': cat,
        })
    return out


async def fetch_game(page, slug):
    out_path = GAMES_HTML / f'{slug}.html'
    json_path = GAMES_HTML / f'{slug}.json'

    if json_path.exists():
        return json.loads(json_path.read_text(encoding='utf-8'))

    url = f'https://mga.games/games/{slug}'
    try:
        await page.goto(url, wait_until='domcontentloaded', timeout=45000)
    except Exception as e:
        print(f'    goto warn {slug}: {e}')
        return {'slug': slug, 'error': str(e)}
    await page.wait_for_timeout(int(REQUEST_DELAY_S * 1000))
    await accept_cookies(page)
    # Wait for description block to render
    try:
        await page.wait_for_function(
            "() => (document.body && document.body.innerText.includes('RESUMEN'))",
            timeout=8000,
        )
    except Exception:
        pass

    html = await page.content()
    out_path.write_text(html, encoding='utf-8')

    fields = await page.evaluate(EXTRACT_GAME_FIELDS_JS)
    rec = {'slug': slug, 'url': url, **fields}
    json_path.write_text(json.dumps(rec, indent=2, ensure_ascii=False), encoding='utf-8')
    return rec


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            user_agent=USER_AGENT,
            locale='es-ES',
            viewport={'width': 1440, 'height': 900},
        )
        page = await ctx.new_page()

        # ---------- Phase A: discovery ----------
        catalog = []
        for i, (label, key) in enumerate(MARKET_LABELS):
            tiles = await discover_market(page, label, key, is_first=(i == 0))
            catalog.extend(tiles)

        # Write catalog
        cat_path = OUT / 'catalog.csv'
        cols = ['market', 'slug', 'displayed_name', 'category']
        with open(cat_path, 'w', encoding='utf-8-sig', newline='') as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            w.writerows(catalog)
        print(f'\n[catalog] wrote {cat_path.relative_to(PROJECT_ROOT)}: {len(catalog)} (market,slug) rows')
        unique_slugs = sorted({c['slug'] for c in catalog})
        print(f'[catalog] {len(unique_slugs)} unique slugs')

        # ---------- Phase B: per-game scrape ----------
        games = []
        for i, slug in enumerate(unique_slugs, 1):
            if i % 25 == 0:
                print(f'  scraped {i}/{len(unique_slugs)}')
            rec = await fetch_game(page, slug)
            games.append(rec)

        # Write games CSV
        games_path = OUT / 'games.csv'
        gcols = ['slug', 'url', 'title', 'tipo', 'apuesta',
                 'volatilidad', 'premio_max', 'description',
                 'related', 'error']
        with open(games_path, 'w', encoding='utf-8-sig', newline='') as f:
            w = csv.DictWriter(f, fieldnames=gcols, extrasaction='ignore')
            w.writeheader()
            for g in games:
                row = dict(g)
                if isinstance(row.get('related'), list):
                    row['related'] = '|'.join(row['related'])
                row.pop('body_text', None)
                w.writerow(row)
        print(f'[games] wrote {games_path.relative_to(PROJECT_ROOT)}: {len(games)} rows')

        ok = sum(1 for g in games if (g.get('description') or '').strip())
        print(f'[games] {ok}/{len(games)} have non-empty description')

        await browser.close()


if __name__ == '__main__':
    asyncio.run(main())
