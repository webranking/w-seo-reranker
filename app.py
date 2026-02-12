# Streamlit Re-Ranking App

import streamlit as st
import json
import os
import sys
from pathlib import Path
import time
import pandas as pd

# Add the re-ranking module to path
sys.path.insert(0, str(Path(__file__).parent / "re-ranking" / "re-ranking"))

import nest_asyncio
nest_asyncio.apply()

from data_loader import load_aio_data
from scraper import scrape_content
from optimizer import ranker_optimize_content

# --- PROMPT LOADING HELPERS ---
PROMPT_DIR = Path(__file__).parent / "re-ranking" / "re-ranking" / "input"

def load_default_prompt(filename):
    try:
        with open(PROMPT_DIR / filename, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Errore caricamento {filename}: {e}"

# Initialize session state for prompts
if 'critic_prompt' not in st.session_state:
    st.session_state.critic_prompt = load_default_prompt("critical_prompt.md")
if 'initial_prompt' not in st.session_state:
    st.session_state.initial_prompt = load_default_prompt("initial_content_prompt.md")
if 'optimizer_prompt' not in st.session_state:
    st.session_state.optimizer_prompt = load_default_prompt("optimizer_prompt.md")

# Page config
st.set_page_config(
    page_title="AI Overview Content Strategist",
    page_icon="🤖",
    layout="wide"
)

# Styling
st.markdown("""
<style>
    .reportview-container {
        background: #ffffff
    }
    .sidebar .sidebar-content {
        background: #f0f2f6
    }
    h1 {
        color: #1E1E1E;
    }
    .stSuccess {
        background-color: #d4edda;
        color: #155724;
    }
    .stInfo {
        background-color: #d1ecf1;
        color: #0c5460;
    }
</style>
""", unsafe_allow_html=True)

# sidebar configuration
st.sidebar.title("🤖 AI Strategist Agent")
st.sidebar.markdown("---")

# Agent Status Placeholders in Sidebar
status_header = st.sidebar.empty()
status_details = st.sidebar.empty()

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Configurazione")

# Inputs

target_query = st.sidebar.text_input("Query da analizzare", placeholder="Es. consulenza strategica digitale")

start_text_option = st.sidebar.radio(
    "Contenuto di partenza",
    ["Genera automaticamente (Draft)", "Inserisci testo manuale"]
)

starting_text = ""
if start_text_option == "Inserisci testo manuale":
    starting_text = st.sidebar.text_area("Risposta Attuale", height=200, placeholder="Incolla qui il tuo contenuto da ottimizzare...")


gemini_model = st.sidebar.selectbox(
    "Modello AI",
    ["gemini-3-flash-preview", "gemini-3-pro-preview", "gemini-2.5-pro",],
    index=0
)
max_iterations = st.sidebar.number_input("Iterazioni Ottimizzazione", min_value=1, max_value=5, value=3)

# Cache hidden options - Commented out as per user request
# with st.sidebar.expander("Opzioni Avanzate (Cache)"):
#     use_cache_aio = st.checkbox("Usa cache AIO", value=False)
#     use_cache_scraping = st.checkbox("Usa cache Scraping", value=False)
use_cache_aio = False
use_cache_scraping = False

# Prompt Customization
with st.sidebar.expander("⚙️ Personalizza Prompt"):
    st.info("Modifica i prompt usati dall'AI durante l'ottimizzazione.")
    st.session_state.critic_prompt = st.text_area(
        "Analista Critico", 
        value=st.session_state.critic_prompt, 
        height=300,
        help="Prompt usato per analizzare il gap tra il contenuto e il benchmark AIO."
    )
    st.session_state.initial_prompt = st.text_area(
        "Generazione Iniziale", 
        value=st.session_state.initial_prompt, 
        height=300,
        help="Prompt usato per generare la prima bozza (se non fornita)."
    )
    st.session_state.optimizer_prompt = st.text_area(
        "Ottimizzatore", 
        value=st.session_state.optimizer_prompt, 
        height=300,
        help="Prompt usato per applicare le direttive e riscrivere il contenuto ad ogni iterazione."
    )
    
    if st.button("🔄 Ripristina Default"):
        st.session_state.critic_prompt = load_default_prompt("critical_prompt.md")
        st.session_state.initial_prompt = load_default_prompt("initial_content_prompt.md")
        st.session_state.optimizer_prompt = load_default_prompt("optimizer_prompt.md")
        st.rerun()


# Main Content Area
st.title("🔍 AI Semantic Re-Ranker")

if not target_query:
    st.info("👈 Inserisci una query nella sidebar per iniziare l'analisi.")
else:
    # Action Button
    if st.sidebar.button("🚀 Avvia Analisi", type="primary"):
        
        # Prepare the query dictionary (single query mode)
        # Note: If generating automatically, passing empty string to scraper/optimizer triggers generation
        queries = {target_query: starting_text}
        
        OUTPUT_DIR = "re-ranking/re-ranking/output"
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        # --- PHASE 1: DATA ACQUISITION ---
        status_header.header("📡 Acquisizione Dati")
        status_details.info(f"Recupero AI Overview per: **{target_query}**")
        
        with st.status("Recupero AI Overview in corso...", expanded=True) as status_box:
            st.write("Connessione a DataForSEO...")
            aio_data = load_aio_data(
                queries=queries,
                full_data_cache_path=f"{OUTPUT_DIR}/aio_data_full.json",
                filtered_data_cache_path=f"{OUTPUT_DIR}/aio_data.json",
                force_fetch=not use_cache_aio
            )
            st.write("✅ Dati AI Overview acquisiti.")
            
            st.write("Scraping contenuti competitor...")
            scraped_data, cleaned_scraped_data = scrape_content(
                queries=queries,
                aio_data=aio_data,
                cache_path=f"{OUTPUT_DIR}/scraped_content.json",
                cleaned_cache_path=f"{OUTPUT_DIR}/cleaned_scraped_content.json",
                parallel_tasks=5,
                timeout=60000,
                force_scrape=not use_cache_scraping
            )
            st.write("✅ Scraping completato.")
            status_box.update(label="Acquisizione Dati Completata", state="complete", expanded=False)

        # --- AIO DATA VISUALIZATION ---
        aio_full_path = f"{OUTPUT_DIR}/aio_data_full.json"
        if os.path.exists(aio_full_path):
            try:
                with open(aio_full_path, 'r', encoding='utf-8') as f:
                    aio_full_data = json.load(f)
                
                # Debug: log delle chiavi disponibili nel file AIO
                available_keys = list(aio_full_data.keys())
                print(f"[DEBUG AIO] Chiavi disponibili nel file: {available_keys}")
                print(f"[DEBUG AIO] Query cercata: '{target_query}'")
                
                query_data = aio_full_data.get(target_query, [])
                
                print(f"[DEBUG AIO] Risultato lookup: {len(query_data)} elementi trovati")
                if not query_data:
                    print(f"[DEBUG AIO] ⚠️ Nessun dato trovato! Verificare che la query corrisponda esattamente a una delle chiavi.")
                
                if query_data:
                    with st.expander(f"📚 Fonti Recuperate ({len(query_data)} sezioni AIO)", expanded=False):
                        for item in query_data:
                            title = item.get('title') or "Fonte primaria"
                            refs = item.get('references', [])
                            text_preview = item.get('text', '')
                            
                            st.markdown(f"### {title}")
                            st.caption(f"{len(refs)} link trovati")
                            st.text(text_preview)
                            
                            if refs:
                                with st.expander("Visualizza URL"):
                                    for r in refs:
                                        url = r.get('url')
                                        st.markdown(f"- [{url}]({url})")
                            st.divider()
                else:
                    st.error("⚠️ Nessun dato AIO trovato per questa query. Impossibile procedere.")
                    st.stop()
            except Exception as e:
                st.warning(f"Impossibile caricare anteprima fonti: {e}")
                st.stop()

        # --- SCRAPED CONTENT VISUALIZATION ---
        scraped_full_path = f"{OUTPUT_DIR}/scraped_content.json"
        
        scraped_query_data = [] # Default empty
        
        if os.path.exists(scraped_full_path):
            try:
                with open(scraped_full_path, 'r', encoding='utf-8') as f:
                    scraped_full_data = json.load(f)
                
                scraped_query_data = scraped_full_data.get(target_query, [])
                
                if scraped_query_data:
                    # Flatten references list for easier display
                    all_scraped_refs = []
                    for item in scraped_query_data:
                        for ref in item.get('references', []):
                            all_scraped_refs.append(ref)
                    
                    if all_scraped_refs:
                        with st.expander(f"🔎 Esito Scraping ({len(all_scraped_refs)} URL analizzati)", expanded=False):
                            for ref in all_scraped_refs:
                                url = ref.get('url')
                                content = ref.get('scraped_content', '')
                                
                                if content == "no-anchor":
                                    icon = "❌"
                                    status_text = "No anchor found"
                                    preview = ""
                                elif content == "unsupported-format":
                                    icon = "⛔️"
                                    status_text = "Unsupported format"
                                    preview = ""
                                elif content == "match-error":
                                    icon = "⚠️"
                                    status_text = "Match error"
                                    preview = ""
                                else:
                                    icon = "✅"
                                    status_text = "Contenuto estratto"
                                    preview = f": {content[:100]}..."
                                
                                col_icon, col_url = st.columns([0.1, 0.9])
                                with col_icon:
                                    st.write(icon)
                                with col_url:
                                    st.markdown(f"[{url}]({url})")
                                    if preview:
                                        st.caption(f"{status_text}{preview}")
                                    else:
                                        st.error(status_text)
                else:
                    st.error("Nessun contenuto scansionato trovato per questa query. Impossibile procedere.")
                    st.stop()
                            
            except Exception as e:
                st.warning(f"Impossibile caricare esito scraping: {e}")
                st.stop()
        else:
             st.error("File dei contenuti scansionati non trovato. Impossibile procedere.")
             st.stop()

        # --- CLEANED DATA VALIDATION ---
        # Check if we have valid references to optimize against
        current_cleaned_data = cleaned_scraped_data.get(target_query, [])
        has_valid_refs = False
        if current_cleaned_data:
            for item in current_cleaned_data:
                if item.get('references') and len(item.get('references')) > 0:
                    has_valid_refs = True
                    break
        
        if not has_valid_refs:
            st.error("⚠️ Nessun riferimento valido estratto. Impossibile procedere con l'ottimizzazione.")
            st.stop()

        # --- PHASE 2: OPTIMIZATION ---
        status_header.header("🧠 Ottimizzazione")
        status_details.info("Avvio Agente Ottimizzatore...")
        
        # Helper to display ranking table nicely
        def display_ranking_table(records, title):
            st.subheader(title)
            # Flatten records for dataframe
            table_data = []
            for r in records:
                # Handle both RankerService objects (during runtime if we had them) 
                # and dictionary objects (from JSON output)
                # Since we are running the optimizer function which returns the FINAL struct, 
                # we don't get the intermediate objects unless we modify optimizer to yield.
                # BUT, the optimizer returns full iteration history. We can reconstruct the view.
                pass 
            
            # Since we can't easily yield from the backend function without refactoring it into a generator,
            # we will run the full process and then visualize the steps as if they were happening 
            # (or just show the result steps).
            # To strictly follow "visualize iterative flow", we'll parse the 'iteration_history' from the result.
            pass

        with st.spinner("L'AI sta analizzando, criticando e riscrivendo i contenuti..."):
            optimized_results = ranker_optimize_content(
                scraped_content=cleaned_scraped_data,
                max_iterations=max_iterations,
                model_name=gemini_model,
                critic_prompt_template=st.session_state.critic_prompt,
                initial_content_prompt_template=st.session_state.initial_prompt,
                optimizer_prompt_template=st.session_state.optimizer_prompt,
            )

        # Save results
        with open(f"{OUTPUT_DIR}/content_gen.json", "w", encoding="utf-8") as f:
            json.dump(optimized_results, f, indent=2, ensure_ascii=False)
            
        status_header.header("✅ Completato")
        status_details.success("Analisi terminata con successo.")
        
        # --- VISUALIZATION OF RESULTS ---
        result = optimized_results.get(target_query)
        
        if result:
            # 1. Baseline / Starting Point
            st.markdown("## 🏁 Baseline di Partenza")
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Score AIO (Benchmark)", f"{result.get('aio_content_score', 0):.4f}")
            col2.metric("Nostro Score Iniziale", f"{result.get('first_benchmark_score', 0):.4f}")
            
            start_gap = result.get('first_benchmark_score', 0) - result.get('aio_content_score', 0)
            col3.metric("Gap Iniziale", f"{start_gap:.4f}", delta_color="normal")

            st.markdown("### Testo di Partenza")
            st.info(result.get('starting_text', "Nessun testo iniziale generato."))

            # 2. Iterations
            st.markdown("---")
            st.markdown("## 🔄 Processo Iterativo")
            
            iteration_history = result.get('iteration_history', [])
            baseline_ranking = result.get('baseline_ranking', [])
            
            # We skip index 0 which is just the starting state record
            iterations_only = [x for x in iteration_history if x['iteration'] > 0]
            
            for i, step in enumerate(iterations_only):
                iter_num = step['iteration']
                score = step['score']
                prev_score = iterations_only[i-1]['score'] if i > 0 else result.get('first_benchmark_score', 0)
                delta = score - prev_score
                
                with st.expander(f"Iterazione {iter_num} - Score: {score:.4f} ({'+' if delta >= 0 else ''}{delta:.4f})", expanded=True):
                    
                    col_metrics, col_table = st.columns([1, 2])
                    
                    with col_metrics:
                        # Critique Section
                        st.markdown("#### 🧐 Analisi Critica")
                        critique = step.get('critic_critique', '')
                        if critique:
                            st.write(critique)
                        
                        # Directives Section
                        directives_json = step.get('critic_directives', '[]')
                        try:
                            directives = json.loads(directives_json)
                            if directives:
                                st.markdown("**Direttive:**")
                                for d in directives:
                                    st.warning(f"**{d.get('directive_type', 'Direttiva')}**: {d.get('description', '')}")
                        except:
                            pass

                    with col_table:
                        st.markdown("#### 📊 Ranking Aggiornato")
                        
                        # Construct Ranking Table for this iteration
                        ranking_data = []
                        
                        # Add Baseline competitors
                        for item in baseline_ranking:
                            ranking_data.append({
                                "Type": "Competitor" if "ref" in item['id'] else "Google AIO",
                                "Title": item['title'],
                                "Score": item['score'],
                                "Text": item['text'][:100] + "..." # Preview
                            })
                            
                        # Add Current Iteration Content
                        ranking_data.append({
                            "Type": "✨ NOSTRO CONTENUTO",
                            "Title": f"Iterazione {iter_num}",
                            "Score": score,
                            "Text": step.get('generated_text', '')[:100] + "..."
                        })
                        
                        # Create DF and Sort
                        df = pd.DataFrame(ranking_data)
                        df = df.sort_values(by="Score", ascending=False).reset_index(drop=True)
                        df.index += 1 # 1-based ranking
                        
                        # Highlight our row style (optional, if supported by st.dataframe columns config)
                        st.dataframe(
                            df,
                            column_config={
                                "Score": st.column_config.ProgressColumn(
                                    "Relevance Score",
                                    help="Score attribuito dal Reranker",
                                    format="%.4f",
                                    min_value=0,
                                    max_value=1,
                                ),
                                "Text": st.column_config.TextColumn("Anteprima Testo", width="large")
                            },
                            use_container_width=True
                        )

                    # Resulting Text
                    st.markdown("#### 📝 Testo Completo")
                    st.success(step.get('generated_text', ''))

            # 3. Final Result
            st.markdown("---")
            st.markdown("## 🏆 Risultato Finale")
            
            final_score = result.get('best_optimized_text_score', 0)
            final_delta = final_score - result.get('first_benchmark_score', 0)
            
            st.metric("Score Finale Raggiunto", f"{final_score:.4f}", f"{'+' if final_delta >= 0 else ''}{final_delta:.4f}")
            
            st.text_area("Testo Ottimizzato Finale", value=result.get('best_optimized_text', ''), height=300)
            
            # 4. Export to Google Sheets
            st.markdown("---")
            st.header("📤 Export")
            with st.status("Esportazione su Google Sheets...", expanded=True) as export_status:
                try:
                    from services.sheets_export import export_results_to_sheets
                    sheet_url = export_results_to_sheets(f"{OUTPUT_DIR}/content_gen.json", spreadsheet_title_prefix=f"Re-Ranking: {target_query}")
                    if sheet_url:
                        export_status.update(label="Export Completato", state="complete", expanded=True)
                        st.success(f"✅ Report creato con successo! **[Apri Google Sheet]({sheet_url})**")
                    else:
                        export_status.update(label="Export Fallito", state="error")
                        st.error("Impossibile esportare su Google Sheets. Verifica le credenziali.")
                except Exception as e:
                    export_status.update(label="Export Errore", state="error")
                    st.error(f"Errore durante l'export: {e}")

