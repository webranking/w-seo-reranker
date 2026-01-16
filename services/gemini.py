import time
from typing import List, Dict, Any

from google import genai
from google.genai import types
import numpy as np

from dotenv import load_dotenv
from utils import secrets
import os
import logging

from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)
load_dotenv()


class GeminiService:
    def __init__(self, model_name: str = "gemini-2.5-flash", temperature: float = 0.3):
        # Parametri di configurazione modello
        self.model_name = model_name
        self.temperature = temperature
        self.files = []

        # Try to get API KEY from Environment/Streamlit Secrets first
        self.api_key = os.getenv("GOOGLE_API_KEY")
        
        if not self.api_key:
            # Fallback to GCP Secret Manager (Legacy)
            try:
                self.api_key = secrets.get_secret(
                    name=os.getenv("SECRET_MANAGER_WR_GEMINI_RANKING_ACCESS"),
                    project_id=os.getenv("GCP_PROJECT_ID_RANKING")
                )
            except Exception as e:
                logger.warning(f"Could not retrieve Gemini API Key from GCP: {e}")
        self.client = genai.Client(api_key=self.api_key)

    def upload_file(self, filepath):
        upload = self.client.files.upload(file=filepath)
        self.files.append(upload)

    def generate_content(self, prompt: str) -> str:
        """
        Invia un prompt a Gemini e restituisce la risposta testuale.
        """
        while True:
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=[prompt, *self.files],
                    config=types.GenerateContentConfig(
                        temperature=self.temperature
                    )
                )
                if not response.text:   # response.text can be null
                    continue
                return response.text
            except Exception as e:
                logger.error(f"Errore durante la chiamata a Gemini: {e}", exc_info=True)
                raise e


    def batch_generate_content(self, prompts_data: List[dict]):
        """
        Invia una lista di prompt a Gemini in un'unica chiamata batch.
        """
        try:
            inline_requests = []
            for data in prompts_data:
                # Aggiungi i file di contesto a ogni richiesta
                contents = [data["prompt"], *self.files]
                inline_requests.append({'contents': contents})

            batch_job = self.client.batches.create(
                model=f"models/{self.model_name}",
                src=inline_requests,
                config={
                    'display_name': f"batch-job-{int(time.time())}",
                },
            )
            return batch_job
        except Exception as e:
            logger.error(f"Errore durante la creazione del job batch: {e}", exc_info=True)
            raise e

    # def batch_generate_content(self, requests: List[dict]) -> List[str]:
    #     inline_requests = []
    #     for request in requests:
    #         inline_requests.append({
    #             'contents': [request["prompt"], *self.files]
    #         })
    #
    #     batch_job = self.client.batches.create(
    #         model=f"models/{self.model_name}",
    #         src=inline_requests,
    #         config=types.GenerateContentConfig(
    #             temperature=self.temperature
    #         )
    #     )
    #
    #     print(f"Created batch job: {batch_job.name}")
    #
    #     completed_states = {'JOB_STATE_SUCCEEDED', 'JOB_STATE_FAILED', 'JOB_STATE_CANCELLED', 'JOB_STATE_EXPIRED'}
    #
    #     print(f"Polling status for job: {batch_job.name}")
    #     batch_job = self.client.batches.get(name=batch_job.name)  # Initial get
    #     while batch_job.state.name not in completed_states:
    #         print(f"Current state: {batch_job.state.name}")
    #         time.sleep(30)  # Wait for 30 seconds before polling again
    #         batch_job = self.client.batches.get(name=batch_job.name)
    #
    #     print(f"Job finished with state: {batch_job.state.name}")
    #     if batch_job.state.name == 'JOB_STATE_FAILED':
    #         print(f"Error: {batch_job.error}")
    #
    #     if batch_job.state.name == 'JOB_STATE_SUCCEEDED':
    #         # If batch job was created with inline request
    #         # (for embeddings, use batch_job.dest.inlined_embed_content_responses)
    #         if batch_job.dest and batch_job.dest.inlined_responses:
    #             # Results are inline
    #             print("Results are inline:")
    #             for i, inline_response in enumerate(batch_job.dest.inlined_responses):
    #                 print(f"Response {i + 1}:")
    #                 if inline_response.response:
    #                     # Accessing response, structure may vary.
    #                     try:
    #                         print(inline_response.response.text)
    #                     except AttributeError:
    #                         print(inline_response.response)  # Fallback
    #                 elif inline_response.error:
    #                     print(f"Error: {inline_response.error}")
    #         else:
    #             print("No results found (neither file nor inline).")
    #     else:
    #         print(f"Job did not succeed. Final state: {batch_job.state.name}")
    #         if batch_job.error:
    #             print(f"Error: {batch_job.error}")
    #
    #
    #     # for request in requests:
    #     #     gemini_requests.append({
    #     #         "key": request[key],
    #     #         "request": {
    #     #             "contents": [{
    #     #                 "parts": [{
    #     #                     "text": text,
    #     #                 }]
    #     #             }]
    #     #         }
    #     #     })
    #
    #     # with open("batch-requests.jsonl", "w") as f:
    #     #     for req in gemini_requests:
    #     #         f.write(json.dumps(req) + "\n")

    # def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
    #     """Genera embeddings per una lista di testi in batch."""
    #     if not texts:
    #         return []
    #     # all_embeddings = []
    #     # for text in texts:
    #     try:
    #
    #         result = [
    #             np.array(e.values) for e in self.client.models.embed_content(
    #                 model=EMBEDDING_MODEL,
    #                 contents=texts,
    #                 config=types.EmbedContentConfig(task_type="SEMANTIC_SIMILARITY")).embeddings
    #         ]
    #         # all_embeddings.append(embedding.embeddings)
    #     except Exception as e:
    #         print(f"Errore durante la fase di embedding per il testo: {e}")
    #         return []  # Aggiunge un embedding vuoto in caso di errore
    #     return result










