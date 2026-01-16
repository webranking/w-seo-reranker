# scraper.py

import asyncio
import json
import os
import urllib.parse
from typing import Dict
from playwright.async_api import async_playwright
import requests

# --- Modulo Scraper ---

def get_anchored_text(url: str, text_content: str) -> str:
    """Estrae il testo evidenziato da un URL con anchor text."""
    text_content = " ".join(text_content.split())
    try:
        encoded_fragments = url.split("#:~:text=")[1].split("&text=")
        highlighted_parts = []
        for frag in encoded_fragments:
            frag = frag.replace("-,", "\n")
            start_text, end_text = frag.split(",", 1)

            start_text = (urllib.parse.unquote(start_text)
                          .replace("’", "'")
                          .replace("‘", "'")
                          .replace("\n", " "))
            end_text = (urllib.parse.unquote(end_text)
                        .replace("’", "'")
                        .replace("‘", "'")
                        .replace("\n", " "))

            start_idx = text_content.lower().find(start_text.strip().lower())
            end_idx = text_content.lower().find(end_text.strip().lower(), start_idx + len(start_text))

            if start_idx != -1 and end_idx != -1:
                highlighted = text_content[start_idx:end_idx + len(end_text)]
                highlighted_parts.append(highlighted.strip())
            else:
                print(f"[HIGHLIGHTED] match NOT found for fragment: {start_text, end_text} in {url}")
                return "match-error"
        if highlighted_parts:
          return "\n\n---\n\n".join(highlighted_parts)
    except Exception as e:
        print(f"Exception during anchor text extraction: {e}")
        return "match-error"

async def get_highlighted_text_from_url(url: str, timeout: int):
    """Esegue lo scraping di un singolo URL per estrarre il contenuto."""

    clean_url = url.split("#:~:text=")[0]
    if any(ext in clean_url for ext in ['.pdf', '.jpg', '.png']) or "youtube.com" in clean_url:
        return "unsupported-format"

    if "#:~:text=" not in url: return "no-anchor"

    async with async_playwright() as p:
        browser = None
        try:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(clean_url, timeout=timeout, wait_until='domcontentloaded')
            body_text = await page.locator('body').inner_text()
            return get_anchored_text(url, body_text)
        except Exception as e:
            print(f"[ERROR] Playwright failed for {url}: {e}. Falling back to requests.")
            try:
              r = requests.get(clean_url, timeout=10)
              if r.status_code == 200:
                return r.text
              return f"error - {r.status_code}"
            except Exception as e2:
              print(f"[ERROR fallback] requests failed: {url} - {e2}")
              return f"error - {e2}"
        finally:
          if browser:
            await browser.close()

async def scrape_and_populate_references(aio_data: Dict, parallel_tasks: int, timeout: int) -> Dict:
    """Esegue lo scraping in parallelo per tutti gli URL di riferimento."""
    unique_urls = {
        ref['url']
        for sections in aio_data.values()
        for section in sections
        for ref in section.get('references', [])
    }

    if not unique_urls:
        print("Nessun URL unico da processare.")
        return aio_data

    print(f"Trovati {len(unique_urls)} URL unici da sottoporre a scraping.")

    semaphore = asyncio.Semaphore(parallel_tasks)

    async def limited_scrape(url):
        async with semaphore:
            return await get_highlighted_text_from_url(url, timeout)

    tasks = {url: asyncio.create_task(limited_scrape(url)) for url in unique_urls}
    results = await asyncio.gather(*tasks.values(), return_exceptions=True)

    url_to_content = {}
    for i, url in enumerate(tasks.keys()):
        result = results[i]
        if isinstance(result, Exception):
            print(f"⚠️  Task per l'URL {url} ha generato un'eccezione: {result}")
            url_to_content[url] = f"ERROR: {result}"
        else:
            url_to_content[url] = result

    populated_data = json.loads(json.dumps(aio_data))
    for sections in populated_data.values():
        for section in sections:
            for ref in section.get('references', []):
                ref['scraped_content'] = url_to_content.get(ref['url'], "URL_NOT_PROCESSED")

    return populated_data

def scrape_content(queries: Dict[str, str], aio_data: Dict, cache_path: str, cleaned_cache_path: str, parallel_tasks: int, timeout: int, force_scrape: bool) -> (Dict, Dict):
    """Gestisce la logica di scraping, inclusa la cache. È una funzione sincrona."""
    if not force_scrape and os.path.exists(cache_path):
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                print(f"Contenuto scraped caricato dalla cache: {cache_path}")
                data = json.load(f)
                if data:
                    return data
                print("Cache trovata ma vuota. Procedo con lo scraping.")
        except (json.JSONDecodeError, FileNotFoundError):
            print("Cache del contenuto scraped non trovata o corrotta. Procedo con lo scraping.")

    scraped_data = asyncio.run(scrape_and_populate_references(aio_data, parallel_tasks, timeout))

    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(scraped_data, f, indent=2, ensure_ascii=False)
    print(f"Contenuto scraped salvato nella cache: {cache_path}")

    # Produci anche un file pulito che contiene unicamente le fonti utilizzabili
    cleaned_data = {}

    for query in scraped_data:
        aio_sources = scraped_data[query][0]

        valid_sources = []

        for source in aio_sources['references']:
            if source['scraped_content'] not in ["no-anchor", "match-error"]:
                valid_sources.append(source)

        cleaned_data[query] = []
        cleaned_data[query].append(
            {
                "title": aio_sources['title'],
                "text": aio_sources['text'],
                "starting_text": queries.get(query, ""),
                "references": valid_sources
            }
        )

    with open(cleaned_cache_path, "w", encoding="utf-8") as f:
        json.dump(cleaned_data, f, indent=2, ensure_ascii=False)
    print(f"Contenuto scraped salvato nella cache: {cleaned_cache_path}")

    return scraped_data, cleaned_data