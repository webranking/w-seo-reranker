# data_loader.py

import os
import json
from typing import List, Dict

from services.dataforseo import DataForSeoService

# --- Modulo Data Loader ---

def request_and_retrieve_serp(queries: Dict[str, str]) -> dict:
    data_for_seo = DataForSeoService() # Assicurati che questa classe sia definita o importata

    aio_full_data = {}

    for index, query in enumerate(queries.keys()):
        print(f"[{index + 1}/{len(queries)}] Recupero AIO per la query: '{query}'")
        try:
            post_data = data_for_seo.post_request(keyword_list=[query], get_aio=True)
            task_id = post_data["tasks"][0]["id"]
            serp_data = data_for_seo.get_task_polling(task_id)

            results = serp_data["tasks"][0].get("result", [])
            aio_results = next((r for r in results[0]["items"] if r["type"] == "ai_overview"), None) \
                if results and results[0].get("items") else None

            aio_data = []
            if aio_results:
                for item in aio_results.get("items", []):
                    section = {
                        "title": item.get("title"),
                        "text": item.get("text"),
                        "references": [{"url": ref["url"]} for ref in item.get("references", []) if ref.get("url")]
                    }
                    aio_data.append(section)
            aio_full_data[query] = aio_data
        except Exception as e:
            print(f"Contenuto AIO non disponibile - error: {e}")
            aio_full_data[query] = []

    return aio_full_data


def load_aio_data(
        queries: Dict[str, str],
        full_data_cache_path: str,
        filtered_data_cache_path: str,
        force_fetch: bool
) -> Dict:
    """Carica i dati AIO, usando la cache se disponibile."""
    if not force_fetch and os.path.exists(filtered_data_cache_path):
        try:
            with open(filtered_data_cache_path, 'r', encoding='utf-8') as f:
                print(f"Dati AIO caricati dalla cache: {filtered_data_cache_path}")
                data = json.load(f)
                if data:  # Assicurati che la cache non sia vuota
                    return data
                print("Cache AIO trovata ma vuota. Procedo con il fetch.")
        except (json.JSONDecodeError, FileNotFoundError):
            print("Cache AIO corrotta o non trovata. Procedo con il fetch.")

    aio_full_data = request_and_retrieve_serp(queries=queries)

    # Dati completi
    with open(full_data_cache_path, "w", encoding="utf-8") as f:
        json.dump(aio_full_data, f, indent=2, ensure_ascii=False)

    filtered_data = {
        query: [sections[0]]
        for query, sections in aio_full_data.items()
        if sections  # Assicurati che la lista di sezioni non sia vuota
    }

    # Salva i dati filtrati
    with open(filtered_data_cache_path, "w", encoding="utf-8") as f:
        json.dump(filtered_data, f, indent=2, ensure_ascii=False)
    print(f"Dati AIO filtrati e salvati nella cache")

    # Restituisci i dati filtrati
    return filtered_data