# main.py

import os
import json
import nest_asyncio

# Importa le configurazioni e le funzioni dai moduli separati
import config
from data_loader import load_aio_data
from scraper import scrape_content

from analyzer import analyze_sources
from optimizer import optimize_content, ranker_optimize_content


def main():
    """
    Script principale per eseguire il flusso di lavoro di acquisizione e scraping.
    """
    # Applica nest_asyncio per gestire l'event loop, utile in ambienti come Jupyter/Spyder
    nest_asyncio.apply()

    # Assicurati che la directory di output esista
    if not os.path.exists(config.OUTPUT_DIR):
        os.makedirs(config.OUTPUT_DIR)

    # --- FASE 1: Acquisizione Dati AIO ---
    print("\n--- FASE 1: Acquisizione Dati AIO ---")
    aio_data = load_aio_data(
        queries=config.QUERIES_TO_ANALYZE,
        full_data_cache_path=config.AIO_FULL_DATA_OUTPUT,
        filtered_data_cache_path=config.AIO_DATA_OUTPUT,
        force_fetch=config.FORCE_FETCH_AIO
    )
    print(f"\nFase 1 completata. Trovati dati AIO per {len(aio_data)} query.")
    print(f"I risultati sono stati salvati in '{config.AIO_DATA_OUTPUT}'.")

    # --- FASE 2: Scraping del Contenuto ---
    print("\n--- FASE 2: Scraping del Contenuto ---")

    # Carica i dati dalla fase precedente per lo scraping
    try:
        with open(config.AIO_DATA_OUTPUT, 'r', encoding='utf-8') as f:
            aio_data_for_scraping = json.load(f)
    except FileNotFoundError:
        print(f"❌ Errore: File '{config.AIO_DATA_OUTPUT}' non trovato. Esegui prima la Fase 1.")
        return  # Esce dallo script se il file di input non esiste

    scraped_data, cleaned_scraped_data = scrape_content(
        queries=config.QUERIES_TO_ANALYZE,
        aio_data=aio_data_for_scraping,
        cache_path=config.SCRAPING_OUTPUT,
        cleaned_cache_path=config.CLEANED_SCRAPING_OUTPUT,
        parallel_tasks=config.SCRAPING_PARALLEL_TASKS,
        timeout=config.SCRAPING_TIMEOUT,
        force_scrape=config.FORCE_SCRAPE
    )
    print(f"\n✅ Fase 2 completata. Scraping eseguito.")
    print(f"I risultati arricchiti sono stati salvati in '{config.SCRAPING_OUTPUT}'.")


    # --- FASE 3: Analisi Semantica ---
    print("\n--- FASE 3: Analisi Semantica ---")
    with open(config.SCRAPING_OUTPUT, "r", encoding="utf-8") as f:
        scraped_data = json.load(f)

    with open(config.CLEANED_SCRAPING_OUTPUT, "r", encoding="utf-8") as f:
        cleaned_scraped_data = json.load(f)

    # embeddings = analyze_sources(scraped_data, config.EMBEDDING_MODEL)
    # with open(config.EMBEDDINGS_OUTPUT, "w", encoding="utf-8") as f:
    #     json.dump(embeddings, f, indent=2, ensure_ascii=False)
    print(f"\n✅ Fase 3 completata. Risultati salvati in '{config.EMBEDDINGS_OUTPUT}'.")

    with open(config.EMBEDDINGS_OUTPUT, "r", encoding="utf-8") as f:
        embeddings = json.load(f)

    # --- FASE 4: Ottimizzazione del Contenuto ---
    print("\n--- FASE 4: Ottimizzazione del Contenuto ---")
    optimized_results = optimize_content(
        embeddings,
        config.GEMINI_MODEL,
        config.EMBEDDING_MODEL,
        config.PROMPT,
        config.MAX_ITERATIONS,
        config.SIMILARITY_BENCHMARK_OFFSET
    )

    optimized_results = ranker_optimize_content(
        scraped_content=cleaned_scraped_data,
        max_iterations=config.MAX_ITERATIONS,
    )
    with open(config.CONTENT_GEN_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(optimized_results, f, indent=2, ensure_ascii=False)
    print(f"\n✅ Fase 4 completata. Risultati finali salvati in '{config.CONTENT_GEN_OUTPUT}'.")

    # Stampa riepilogo finale
    print("\n--- RIEPILOGO RISULTATI OTTIMIZZAZIONE ---")
    for query, result in optimized_results.items():
        print("\n" + "="*40)
        print(f"Query: {query}")
        print(f"Score Finale: {result.get('best_optimized_text_score', -1):.4f} (Benchmark AIO: {result.get('aio_content_score', -1):.4f})")
        print(f"Iterazioni eseguite: {result.get('iterations_ran', 0)}")
        print("\nTesto Ottimizzato Finale:")
        print(result.get('best_optimized_text', 'N/A'))
        print("="*40)


if __name__ == "__main__":
    main()