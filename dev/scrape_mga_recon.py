"""
Recon: load mga.games with a real browser, dismiss cookie banner + market
modal, capture rendered /games listing and a sample per-game page. Saves
HTML + screenshots + visible text + network log to dev/_recon/.
"""
import asyncio
import json
import re
from pathlib import Path

from playwright.async_api import async_playwright

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = PROJECT_ROOT / 'dev' / '_recon'
OUT_DIR.mkdir(parents=True, exist_ok=True)


DISMISS_JS = r"""
(() => {
  const log = [];
  // Click any 'Aceptar' / 'Accept' button
  document.querySelectorAll('button, a').forEach(el => {
    const t = (el.innerText || '').trim().toLowerCase();
    if (t === 'aceptar cookies' || t === 'aceptar' || t === 'accept all' || t === 'accept cookies') {
      el.click();
      log.push('clicked: ' + t);
    }
  });
  // Click España in the market chooser
  document.querySelectorAll('button, a, div, li, span').forEach(el => {
    const t = (el.innerText || '').trim();
    if (t === 'España') {
      el.click();
      log.push('clicked: España');
    }
  });
  return log;
})()
"""


async def visit(page, url, label, network_log, dismiss=True):
    network_log.clear()
    print(f'\n=== {label}: {url} ===')
    try:
        await page.goto(url, wait_until='domcontentloaded', timeout=45000)
    except Exception as e:
        print(f'  goto warn: {e}')
    await page.wait_for_timeout(3000)

    if dismiss:
        for attempt in range(3):
            log = await page.evaluate(DISMISS_JS)
            if log:
                print(f'  dismiss attempt {attempt+1}: {log}')
                await page.wait_for_timeout(1500)
            else:
                break

    try:
        await page.wait_for_load_state('networkidle', timeout=8000)
    except Exception:
        pass
    await page.wait_for_timeout(2000)

    title = await page.title()
    html = await page.content()
    print(f'  title={title!r}  html_size={len(html)}')

    (OUT_DIR / f'{label}.html').write_text(html, encoding='utf-8')
    await page.screenshot(path=str(OUT_DIR / f'{label}.png'), full_page=True)

    links = await page.evaluate(
        "Array.from(document.querySelectorAll('a[href]')).map(a => a.getAttribute('href'))"
    )
    visible_text = await page.evaluate(
        "document.body ? document.body.innerText : ''"
    )
    (OUT_DIR / f'{label}.text.txt').write_text(visible_text or '', encoding='utf-8')

    # Look for tiles: any element with image whose src or class hints at a game
    img_data = await page.evaluate(r"""
      Array.from(document.querySelectorAll('img')).slice(0, 60).map(img => ({
        src: img.getAttribute('src') || '',
        alt: img.getAttribute('alt') || '',
        parent_href: img.closest('a') ? img.closest('a').getAttribute('href') : '',
      }))
    """)

    return {
        'url': url, 'title': title, 'html_size': len(html),
        'links': links, 'imgs': img_data,
        'network': list(network_log),
    }


async def main():
    network_log: list[dict] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                       'AppleWebKit/537.36 (KHTML, like Gecko) '
                       'Chrome/124.0 Safari/537.36',
            locale='es-ES',
            viewport={'width': 1440, 'height': 900},
        )
        page = await ctx.new_page()
        page.on('request', lambda req: network_log.append({
            'method': req.method, 'url': req.url, 'rt': req.resource_type,
        }))

        results = {}
        results['home'] = await visit(page, 'https://mga.games/', 'home', network_log)
        # After picking España on home, the choice persists in the SPA state — go to /games
        results['games_after_pick'] = await visit(
            page, 'https://mga.games/games', 'games_after_pick', network_log, dismiss=True)

        # Also try direct type filter
        results['slots3'] = await visit(
            page, 'https://mga.games/games?type=slots-3', 'slots3', network_log, dismiss=True)

        all_links = []
        for k in ('home', 'games_after_pick', 'slots3'):
            for href in (results.get(k, {}).get('links') or []):
                if not href:
                    continue
                if href.startswith(('http', 'mailto:', 'tel:', '#', 'javascript:')):
                    continue
                all_links.append(href)
        all_links = sorted(set(all_links))
        print(f'\n  All unique internal links across pages: {len(all_links)}')
        for l in all_links:
            print(f'    {l}')

        # Per-game link pattern guess: anything starting with /game/ or /games/
        per_game = [l for l in all_links if re.match(r'/games?/[^/?#]+/?$', l)]
        print(f'\n  Per-game link candidates: {len(per_game)}')
        for l in per_game[:20]:
            print(f'    {l}')

        # Imgs from games page often expose game-specific URLs/alt texts
        print(f'\n  Sample imgs from games_after_pick:')
        for im in (results.get('games_after_pick', {}).get('imgs') or [])[:20]:
            print(f"    src={im['src'][:80]} alt={im['alt']!r} href={im['parent_href']}")

        # If we have per-game, fetch one
        candidate = None
        for l in per_game:
            candidate = l
            break
        if candidate:
            full = candidate if candidate.startswith('http') else f'https://mga.games{candidate if candidate.startswith("/") else "/" + candidate}'
            results['game_sample'] = await visit(
                page, full, 'game_sample', network_log, dismiss=True)

        # Network summary
        net_unique = []
        seen = set()
        for k, v in results.items():
            for r in (v.get('network') or []):
                u = r['url']
                if any(x in u for x in ('googletag', 'gtag/js', 'fonts.gstatic',
                        'fonts.googleapis', 'cdn.jsdelivr', '.woff', '.woff2',
                        '.svg', '.png', '.jpg', '.jpeg', '.gif', '.css', '.ico',
                        '.webp', 'google-analytics')):
                    continue
                key = (r['method'], u.split('?')[0])
                if key in seen:
                    continue
                seen.add(key)
                net_unique.append(r)
        (OUT_DIR / 'network_summary.json').write_text(
            json.dumps(net_unique, indent=2, ensure_ascii=False), encoding='utf-8')
        print(f'\n  {len(net_unique)} unique non-static endpoints in network_summary.json')

        await browser.close()
    print(f'\nArtefacts in {OUT_DIR.relative_to(PROJECT_ROOT)}/')


if __name__ == '__main__':
    asyncio.run(main())
