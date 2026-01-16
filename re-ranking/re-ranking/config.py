from pathlib import Path

# --- DIRECTORY SETUP ---
BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"

# --- INPUT PRINCIPALE ---
QUERIES_TO_ANALYZE = {
    "Strategie di marketing omnicanale per un brand di abbigliamento con negozi fisici e online": "",
    # "consent mode": "Consent Mode è una funzionalità di Google a supporto degli inserzionisti europei e britannici che consente di comunicare e onorare le scelte di consenso degli utenti, rispettando il Digital Markets Act – in vigore dal 6 Marzo 2024 – e migliorando i dati sulle conversioni. Grazie a Consent Mode, Google ottiene l'indicazione sul consenso dell'utente, influenzando così l'attività dei propri tag e degli SDK così da garantire la privacy durante le attività di conversione e di remarketing. Oltre a questo, offre anche strumenti per recuperare informazioni sulle conversioni perse a causa di mancati consensi, migliorando la comprensione delle performance e l'ottimizzazione delle campagne.",
    # "consulenza strategica digitale": "La nostra consulenza strategica ha l'obiettivo di fornire ai brand un approccio integrato per avere una visione unitaria delle attività di digital marketing da attivare. Avere a disposizione competenze non basta: il valore aggiunto che possiamo offrirti grazie alla nostra consulenza è mettere a disposizione l'insieme di attività, conoscenze e visione di mercato più funzionali alle scelte che dovrai affrontare."
}

# --- PARAMETRI DI CACHE E OUTPUT ---
AIO_FULL_DATA_OUTPUT = f"{OUTPUT_DIR}/aio_data_full.json"
AIO_DATA_OUTPUT = f"{OUTPUT_DIR}/aio_data.json"
SCRAPING_OUTPUT = f"{OUTPUT_DIR}/scraped_content.json"
CLEANED_SCRAPING_OUTPUT = f"{OUTPUT_DIR}/cleaned_scraped_content.json"
EMBEDDINGS_OUTPUT = f"{OUTPUT_DIR}/embeddings.json"
CONTENT_GEN_OUTPUT = f"{OUTPUT_DIR}/content_gen.json"

# --- PARAMETRI DI SCRAPING ---
SCRAPING_PARALLEL_TASKS = 5
SCRAPING_TIMEOUT = 60000

# --- PARAMETRI DI OTTIMIZZAZIONE ---
GEMINI_MODEL = "gemini-3-pro-preview"
MAX_ITERATIONS = 3

# --- FLAG PER FORZARE L'AGGIORNAMENTO ---
FORCE_FETCH_AIO = True
FORCE_SCRAPE = True