from dotenv import load_dotenv
import os
import time
import requests # trigger deployment


from typing import List, Dict

load_dotenv()

class DataForSeoService:
    """Interagisce con le API di DataForSEO per recuperare i dati SERP e AIO."""
    def __init__(self):
        # Try to get credentials from Environment/Streamlit Secrets first
        login = os.getenv("DATAFORSEO_LOGIN") or "innovation@webranking.it"
        password = os.getenv("DATAFORSEO_PASSWORD")

        if not password:
            # Fallback to GCP Secret Manager (Legacy) - lazy import to avoid dependency issues
            try:
                from utils import secrets
                password = secrets.get_secret(name=os.getenv("DATAFORSEO_SECRET"), project_id=os.getenv("GCP_PROJECT_ID_RANKING"))
            except Exception as e:
                print(f"Warning: Could not retrieve DataForSEO secret from GCP: {e}")
                password = None

        self.credentials = (login, password)

    def post_request(self, keyword_list: List[str], get_aio: bool = False) -> Dict:
        """Invia una richiesta per creare un task di analisi SERP."""
        request_data = []
        for keyword in keyword_list:
            item = {
                "keyword": keyword,
                "location_name": "Italy",
                "language_name": "Italian",
                "device": "desktop",
            }
            if get_aio:
                item["load_async_ai_overview"] = True
            request_data.append(item)

        response = requests.post(
            "https://api.dataforseo.com/v3/serp/google/organic/task_post",
            auth=self.credentials,
            json=request_data
        )
        response.raise_for_status()
        return response.json()

    def get_tasks_ready(self) -> dict:
        """Controlla quali task sono pronti per essere scaricati."""
        response = requests.get(
            "https://api.dataforseo.com/v3/serp/google/organic/tasks_ready",
            auth=self.credentials,
        )
        response.raise_for_status()
        return response.json()

    def get_task(self, task_id: str) -> dict:
        """Recupera il risultato di un task specifico."""
        response = requests.get(
            f"https://api.dataforseo.com/v3/serp/google/organic/task_get/advanced/{task_id}",
            auth=self.credentials,
        )
        response.raise_for_status()
        return response.json()

    def get_task_polling(self, task_id: str, require_aio: bool = True) -> dict:
        """Attende che un task sia pronto, controllando a intervalli regolari.
        
        Args:
            task_id: ID del task da recuperare.
            require_aio: Se True, dopo il completamento del task verifica che
                         ai_overview sia presente in item_types. Se assente,
                         ritenta fino a 5 volte con 15s di pausa.
        """
        # Fase 1: Attesa completamento task
        for i in range(1, 60):
            data = self.get_task(task_id)
            status_code = data["tasks"][0]["status_code"]
            status_message = data["tasks"][0].get("status_message", "")
            print(f"[AIO] Polling tentativo {i} - status_code: {status_code}, message: {status_message} [{task_id}]")
            
            if status_code == 20000:
                break
            print(f"\tData is not ready, wait 30 seconds and retry - [{task_id}]")
            time.sleep(30)
        else:
            raise Exception(f"Could not retrieve data after 60 polling attempts - [{task_id}]")

        # Log diagnostico sugli item_types
        results = data["tasks"][0].get("result", [])
        if results:
            item_types = results[0].get("item_types", [])
            print(f"[AIO] item_types nella risposta: {item_types} [{task_id}]")
        else:
            print(f"[AIO] ⚠️ Nessun result nel task [{task_id}]")
            return data

        # Fase 2: Se richiesto AIO, verifica che sia presente
        if require_aio and "ai_overview" not in item_types:
            print(f"[AIO] ⚠️ ai_overview non presente in item_types. Avvio retry aggiuntivi...")
            for retry in range(1, 6):
                print(f"[AIO] Retry AIO {retry}/5 - attesa 15s... [{task_id}]")
                time.sleep(15)
                data = self.get_task(task_id)
                results = data["tasks"][0].get("result", [])
                if results:
                    item_types = results[0].get("item_types", [])
                    print(f"[AIO] Retry {retry} - item_types: {item_types} [{task_id}]")
                    if "ai_overview" in item_types:
                        print(f"[AIO] ✅ ai_overview trovata al retry {retry}!")
                        break
            else:
                print(f"[AIO] ⚠️ ai_overview NON trovata dopo 5 retry aggiuntivi [{task_id}]")

        return data