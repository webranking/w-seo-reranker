# optimizer.py
import json
import time
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from typing import Dict, List
from pathlib import Path

from services.gemini import GeminiService
from services.ranker import RankerService


def optimize_content(
        analysis_results: Dict,
        generative_model: str,
        embedding_model: str,
        prompt: str,
        iterations: int,
        benchmark_offset: float
) -> Dict:
    """
    Esegue il loop di ottimizzazione con Gemini per generare un nuovo testo
    che superi in similarità le fonti esistenti.
    """
    print("Inizializzazione del servizio generativo Gemini...")
    gemini_service = GeminiService(model_name=generative_model)
    optimized_content = {}

    queries_to_process = list(analysis_results.keys())
    for i, query in enumerate(queries_to_process):
        analysis = analysis_results[query]
        print(f"\n[{i + 1}/{len(queries_to_process)}] Inizio ottimizzazione per la query: '{query}'")

        aio_content = analysis.get("aio_content")
        ranked_refs = analysis.get("ranked_references")

        if not ranked_refs or not aio_content:
            print("  -> Nessuna fonte valida o testo AIO su cui basare l'ottimizzazione. Salto.")
            continue

        try:
            # overview_embedding_list = \
            # genai.embed_content(model=embedding_model, content=aio_content, task_type="SEMANTIC_SIMILARITY")[
            #     'embedding']
            # overview_embedding = np.array(overview_embedding_list).reshape(1, -1)

            aio_embedding = np.array(gemini_service.get_embeddings_batch(texts=[aio_content]))
        except Exception as e:
            print(f"  -> Errore nell'embedding del testo AIO: {e}. Salto ottimizzazione.")
            continue

        score_benchmark = ranked_refs[0]["similarity_score"] + benchmark_offset
        print(f"  -> Benchmark di similarità da superare: {score_benchmark:.4f}")

        best_generated_content = "Nessun contenuto generato che ha migliorato lo score."
        best_generated_score = -1.0
        previous_attempt = ""

        for j in range(iterations):
            print(f"    -> Iterazione di ottimizzazione {j + 1}/{iterations}")

            prompt_scores = "\n".join(
                [f"**(Score: {ref['similarity_score']:.2f}):** '{ref['scraped_content'][:300]}...'" for ref in
                 ranked_refs[:3]])
            feedback_prompt = f"\nLa versione precedente era: \"{previous_attempt}\"\nMigliorala per essere semanticamente più vicina al concetto obiettivo." if previous_attempt else ""

            full_prompt = f'**Concetto Obiettivo:** "{aio_content}"\n\n**Contenuti di Riferimento (i migliori esistenti):**\n{prompt_scores}\n{feedback_prompt}\n\n**Tuo Compito:**\n{prompt}'

            generated_text = gemini_service.generate_content(full_prompt)
            if generated_text.startswith("Errore:"):
                print(f"      -> Errore da Gemini: {generated_text}")
                continue
            previous_attempt = generated_text

            try:
                # generated_embedding_list = \
                # genai.embed_content(model=embedding_model, content=generated_text, task_type="SEMANTIC_SIMILARITY")[
                #     'embedding']
                # generated_embedding_np = np.array(generated_embedding_list).reshape(1, -1)
                # current_score = cosine_similarity(overview_embedding, generated_embedding_np)[0][0]
                temp_text_embedding = np.array(gemini_service.get_embeddings_batch(texts=[generated_text]))
                current_score = cosine_similarity(aio_embedding, temp_text_embedding)[0][0]

                print(f"      -> Score ottenuto: {current_score:.4f}")
            except Exception as e:
                print(f"      -> Errore nell'embedding del testo generato: {e}. Salto l'iterazione.")
                continue

            if current_score > best_generated_score:
                best_generated_score = current_score
                best_generated_content = generated_text
                print("      -> Nuovo miglior risultato salvato.")

            if current_score > score_benchmark:
                print(
                    f"      -> 🎉 Successo! Score {current_score:.4f} > Benchmark {score_benchmark:.4f}. Interrompo il ciclo.")
                break

            time.sleep(2)

        optimized_content[query] = {
            "aio_content": aio_content,
            "optimized_text": best_generated_content,
            "optimized_text_score": float(best_generated_score),
            "benchmark_score": float(score_benchmark),
            "iterations_ran": j + 1,
            "references": ranked_refs,
        }

    return optimized_content


def load_prompt_from_file(filepath: str) -> str:
    """Funzione helper per caricare un prompt da un file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()


def print_ranking_table(title: str, records: List[Dict]):
    """Stampa una tabella formattata con i risultati del ranking, ordinandoli per score."""
    # Ordina i record in base allo score, dal più alto al più basso
    sorted_records = sorted(records, key=lambda x: x.score, reverse=True)

    print(f"\n--- {title} ---")
    print(f"{'Rank':<5} | {'Score':<8} | {'ID':<25} | {'Anteprima Testo'}")
    print("-" * 90)

    for i, record in enumerate(sorted_records):
        rank = i + 1
        text_preview = record.content.replace('\n', ' ')[0:100] + "..."
        print(f"{rank:<5} | {record.score:<8.4f} | { record.id:<25} | {text_preview}")
    print("-" * 90)


# --- FUNZIONE PRINCIPALE DA SOSTITUIRE ---
def ranker_optimize_content(
        scraped_content: Dict,
        max_iterations: int,
        model_name: str = "gemini-2.0-flash",
        critic_prompt_template: str = None,
        initial_content_prompt_template: str = None,
        optimizer_prompt_template: str = None,
) -> Dict:
    """
    Esegue il loop di ottimizzazione usando il RankerService come giudice,
    e salva una cronologia dettagliata di ogni iterazione.
    """
    print(f"Inizializzazione dei servizi Gemini ({model_name}) e Ranker...")
    gemini_service = GeminiService(model_name=model_name)
    ranker_service = RankerService()

    # Carica i prompt dai file usando path relativi a questo file se non forniti
    base_path = Path(__file__).parent
    input_dir = base_path / "input"
    
    try:
        if critic_prompt_template is None:
            critic_prompt_template = load_prompt_from_file(str(input_dir / "critical_prompt.md"))
        if initial_content_prompt_template is None:
            initial_content_prompt_template = load_prompt_from_file(str(input_dir / "initial_content_prompt.md"))
        if optimizer_prompt_template is None:
            optimizer_prompt_template = load_prompt_from_file(str(input_dir / "optimizer_prompt.md"))
    except FileNotFoundError as e:
        print(f"Prompt non trovato: {e}")
        return {}

    optimized_content = {}
    queries_to_process = list(scraped_content.keys())

    for i, query in enumerate(queries_to_process):
        print(f"\n[{i + 1}/{len(queries_to_process)}] Inizio ottimizzazione per la query: '{query}'")

        analysis = scraped_content[query][0]
        aio_content = analysis.get("text")
        references = analysis.get("references", [])
        opt_text = analysis.get("starting_text", "")

        if not aio_content or not references:
            print("  -> Dati di input insufficienti. Salto.")
            continue

        # Genera il testo iniziale se non presente
        if not opt_text:
            print("  -> Testo di partenza non trovato, avvio generazione...")
            initial_gen_prompt = initial_content_prompt_template.format(query=query, aio_text=aio_content)
            opt_text = gemini_service.generate_content(initial_gen_prompt)

        # --- Calcolo Baseline ---
        print("  -> Calcolo della baseline di rilevanza...")
        baseline_records_to_rank = [{"id": "aio_content", "title": "Testo AIO Originale", "text": aio_content}]
        for idx, ref in enumerate(references):
            baseline_records_to_rank.append({"id": f"ref_{idx}", "title": f"Fonte Competitor {idx}", "text": ref["scraped_content"]})

        try:
            static_baseline = ranker_service.rank(query=query, records=baseline_records_to_rank)
        except Exception as e:
            print(f"  -> ERRORE durante la chiamata al RankerService per la baseline: {e}. Salto la query.")
            continue

        # --- Inizializzazione per il ciclo di ottimizzazione ---
        current_text_to_optimize = opt_text
        best_text = current_text_to_optimize

        # Valuta lo score del testo di partenza
        initial_opt_response = ranker_service.rank(query=query, records=[{"id": "optimized_iter_0", "title": "Testo di partenza", "text": best_text}])
        first_benchmark_score = initial_opt_response[0].score

        best_score = static_baseline[0].score
        benchmark_text = static_baseline[0].content

        print_ranking_table("RANKING DI PARTENZA", static_baseline + initial_opt_response)
        print(f"Score di partenza del testo da ottimizzare: {first_benchmark_score:.4f}")
        print(f"Benchmark da superare: {best_score:.4f} (ID: {static_baseline[0].id})")

        # Inizializza la cronologia delle iterazioni
        iteration_history = []
        iteration_history.append({
            "iteration": 0,
            "score": first_benchmark_score,
            "critic_critique": "",
            "critic_directives": "",
            "generated_text": opt_text
        })

        # --- CICLO DI OTTIMIZZAZIONE ---
        for j in range(max_iterations):
            print(f"\n    -> Iterazione {j + 1}/{max_iterations}")

            # Fase Critica
            critic_prompt = critic_prompt_template.format(query=query, benchmark_text=benchmark_text, current_text=current_text_to_optimize)
            try:
                critic_response_str = gemini_service.generate_content(critic_prompt)
                critic_response_json = json.loads(critic_response_str.strip().replace("```json", "").replace("```", ""))
            except Exception as e:
                print(f"      -> ERRORE parsing critico: {e}. Interrompo"); break

            # Fase Ottimizzazione
            directives_str = "\n".join([f"- {d['description']}" for d in critic_response_json.get("improvement_directives", [])])
            optimizer_prompt = optimizer_prompt_template.format(current_text=current_text_to_optimize, directives=directives_str)
            new_optimized_text = gemini_service.generate_content(optimizer_prompt)

            # Fase Giudizio
            try:
                validation_response = ranker_service.rank(query=query, records=[{"id": f"optimized_iter_{j + 1}", "text": new_optimized_text, "title":""}])
                new_score = validation_response[0].score
            except Exception as e:
                print(f"      -> ERRORE validazione: {e}. Salto iterazione"); continue

            print_ranking_table(f"RANKING ITERAZIONE #{j + 1}", static_baseline + validation_response)

            # Decisione
            delta = new_score - best_score
            if new_score > best_score:
                print(f"      -> Miglioramento! Score: {new_score:.4f} (Delta: +{delta:.4f}). Aggiorno il testo.")
                best_score = new_score
                best_text = new_optimized_text
            else:
                print(f"      -> Nessun miglioramento. Score: {new_score:.4f} (Delta: {delta:.4f}).")

            current_text_to_optimize = new_optimized_text # Il prossimo ciclo parte dal testo appena generato

            # Salva i dati di questa iterazione
            iteration_history.append({
                "iteration": j + 1,
                "score": new_score,
                "critic_critique": critic_response_json.get("overall_critique", "N/A"),
                "critic_directives": json.dumps(critic_response_json.get("improvement_directives", []), ensure_ascii=False),
                "generated_text": new_optimized_text
            })

        # Salva i risultati finali per la query
        optimized_content[query] = {
            "aio_content": aio_content,
            "aio_content_score": static_baseline[0].score,

            "starting_text": opt_text,
            "first_benchmark_score": first_benchmark_score,

            "best_optimized_text": best_text,
            "best_optimized_text_score": best_score,

            "iterations_ran": j + 1,
            "references": references,
            "iteration_history": iteration_history,
            "baseline_ranking": [
                {"id": r.id, "title": r.title, "text": r.content, "score": r.score} 
                for r in static_baseline
            ]
        }

    return optimized_content
