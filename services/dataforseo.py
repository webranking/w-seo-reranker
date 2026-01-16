from utils import secrets
from dotenv import load_dotenv
import os
import time
import requests

from typing import List, Dict

load_dotenv()

class DataForSeoService:
    """Interagisce con le API di DataForSEO per recuperare i dati SERP e AIO."""
    def __init__(self):
        # Try to get credentials from Environment/Streamlit Secrets first
        login = os.getenv("DATAFORSEO_LOGIN") or "innovation@webranking.it"
        password = os.getenv("DATAFORSEO_PASSWORD")

        if not password:
            # Fallback to GCP Secret Manager (Legacy)
            try:
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

    def get_task_polling(self, task_id: str) -> dict:
        """Attende che un task sia pronto, controllando a intervalli regolari."""

        for i in range(1, 60):
            data = self.get_task(task_id)
            if data["tasks"][0]["status_code"] == 20000:
                return data
            print(f"\tData is not ready, wait 30 seconds and retry - [{task_id}]")
            time.sleep(30)

        raise Exception(f"Could not retrieve data - [{task_id}]")