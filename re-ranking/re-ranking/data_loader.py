# data_loader.py

import os # trigger deployment
import json
from typing import List, Dict

from services.dataforseo import DataForSeoService

# --- Modulo Data Loader ---

def request_and_retrieve_serp(queries: Dict[str, str], max_retries: int = 2) -> dict:
    """Recupera i dati SERP + AI Overview per ogni query, con retry robusto.
    
    Args:
        queries: Dizionario {query: testo}.
        max_retries: Numero massimo di tentativi per l'intera richiesta (post + polling).
    """
    data_for_seo = DataForSeoService()

    aio_full_data = {}

    for index, query in enumerate(queries.keys()):
        print(f"\n{'='*60}")
        print(f"[{index + 1}/{len(queries)}] Recupero AIO per la query: '{query}'")
        print(f"{'='*60}")
        
        aio_data = []
        
        for attempt in range(1, max_retries + 1):
            try:
                print(f"[AIO] Tentativo {attempt}/{max_retries} per query: '{query}'")
                
                # POST - Creazione task
                post_data = data_for_seo.post_request(keyword_list=[query], get_aio=True)
                task_id = post_data["tasks"][0]["id"]
                task_status_code = post_data["tasks"][0].get("status_code", "N/A")
                print(f"[AIO] Task creato - ID: {task_id}, status_code: {task_status_code}")

                # POLLING - Attesa risultati (con verifica AIO)
                serp_data = data_for_seo.get_task_polling(task_id, require_aio=True)

                # Estrazione risultati
                results = serp_data["tasks"][0].get("result", [])
                
                if not results:
                    print(f"[AIO] ⚠️ Nessun result nel task completato [{task_id}]")
                    if attempt < max_retries:
                        print(f"[AIO] Ritento l'intera richiesta...")
                        continue
                    break
                
                items = results[0].get("items", [])
                item_types = results[0].get("item_types", [])
                print(f"[AIO] items totali nella SERP: {len(items)}")
                print(f"[AIO] item_types: {item_types}")
                
                # Cerca ai_overview tra gli items
                aio_results = next((r for r in items if r["type"] == "ai_overview"), None)

                if aio_results:
                    print(f"[AIO] ✅ ai_overview trovata! Estrazione sezioni...")
                    for item in aio_results.get("items", []):
                        section = {
                            "title": item.get("title"),
                            "text": item.get("text"),
                            "references": [{"url": ref["url"]} for ref in item.get("references", []) if ref.get("url")]
                        }
                        aio_data.append(section)
                    print(f"[AIO] ✅ {len(aio_data)} sezioni AIO estratte per query: '{query}'")
                    break  # Successo, esci dal loop dei retry
                else:
                    print(f"[AIO] ⚠️ ai_overview NON trovata tra gli items (type presenti: {[r.get('type') for r in items[:10]]})")
                    if attempt < max_retries:
                        print(f"[AIO] Ritento l'intera richiesta (tentativo {attempt + 1}/{max_retries})...")
                    else:
                        print(f"[AIO] ❌ ai_overview non recuperata dopo {max_retries} tentativi per query: '{query}'")
                        
            except Exception as e:
                print(f"[AIO] ❌ Errore al tentativo {attempt}/{max_retries}: {e}")
                if attempt < max_retries:
                    print(f"[AIO] Ritento l'intera richiesta...")
                else:
                    print(f"[AIO] ❌ Tutti i tentativi falliti per query: '{query}'")

        aio_full_data[query] = aio_data

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