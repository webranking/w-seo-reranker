# analyzer.py

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import google.generativeai as genai
from typing import Dict

from services.gemini import GeminiService


# NOTA: Assicurati di aver configurato la tua API key di Google AI.
# Puoi farlo all'inizio del tuo script main.py con:
# import google.generativeai as genai
# genai.configure(api_key="LA_TUA_API_KEY")

def analyze_sources(scraped_data: Dict, embedding_model: str) -> Dict:
    """
    Analizza il contenuto delle fonti, calcola gli embeddings e la similarità
    del coseno rispetto al testo dell'AI Overview.
    """
    gemini_service = GeminiService(model_name="gemini-2.5-pro")
    analysis_results = {}

    queries_to_process = list(scraped_data.keys())
    for i, query in enumerate(queries_to_process):
        sections = scraped_data[query]
        print(f"[{i + 1}/{len(queries_to_process)}] Analisi per la query: '{query}'")

        if not sections:
            print(f"  -> Nessuna sezione AIO, salto l'analisi.")
            continue

        summary_section = sections[0]
        aio_content = summary_section.get("text", "")
        references = summary_section.get("references", [])

        valid_refs = [
            ref for ref in references
            if
            ref.get("scraped_content") and len(ref["scraped_content"]) > 20 and not ref["scraped_content"].startswith(
                "error")
        ]

        if not aio_content:
            print(f"  -> Nessun testo AIO, salto l'analisi.")
            continue

        if not valid_refs:
            print(f"  -> Nessuna fonte con contenuto valido.")
            analysis_results[query] = {
                "aio_content": aio_content,
                "ranked_references": []
            }
            continue

        print(f"  -> Trovate {len(valid_refs)} fonti valide da processare.")

        texts_to_embed = [aio_content] + [ref["scraped_content"] for ref in valid_refs]

        try:
            # Genera embeddings in batch
            # result = genai.embed_content(model=embedding_model, content=texts_to_embed, task_type="SEMANTIC_SIMILARITY")
            # all_embeddings = result['embedding']
            result = gemini_service.get_embeddings_batch(texts=texts_to_embed)
        except Exception as e:
            print(f"  -> Errore critico durante la chiamata batch di embedding: {e}")
            continue

        # aio_embedding = result[0].embedding
        # sources_embedding = [item.embedding for item in result[1:]]
        #
        # overview_embedding = np.array(aio_embedding).reshape(1, -1)
        # source_embeddings = np.array(sources_embedding)
        #
        # similarities = cosine_similarity(overview_embedding, source_embeddings)[0]

        embeddings_matrix = np.array(result)
        similarity_matrix = cosine_similarity(embeddings_matrix)

        for j, ref in enumerate(valid_refs):
            ref["similarity_score"] = similarity_matrix[0][j+1]

        ranked_refs = sorted(valid_refs, key=lambda x: x["similarity_score"], reverse=True)

        analysis_results[query] = {
            "aio_content": aio_content,
            "ranked_references": ranked_refs
        }

    return analysis_results