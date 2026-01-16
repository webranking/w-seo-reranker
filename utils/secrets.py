import json
import os
from dotenv import load_dotenv
from enum import Enum
# from dateutil.parser import isoparse

import google_crc32c
from google.cloud import secretmanager_v1
from google.oauth2 import service_account, credentials as oauth_credentials
# from google_auth_oauthlib.flow import Flow, InstalledAppFlow
from google.auth.transport.requests import Request
from google.api_core.exceptions import NotFound, FailedPrecondition

load_dotenv()


class SecretReturnType(Enum):
    JSON_OBJECT = "JSON_OBJECT"
    STRING = "STRING"
    BYTES = "BYTES"


def get_secret(
    name,
    version="latest",
    return_type: SecretReturnType = SecretReturnType.STRING,
    project_id=None,
):
    if project_id is None:
        project_id = os.getenv("GCP_PROJECT_ID")
        if not project_id:
            raise ValueError(
                "GOOGLE_CLOUD_PROJECT_ID non trovato nel file .env o nelle variabili d'ambiente."
            )
    client = secretmanager_v1.SecretManagerServiceClient()

    name = f"projects/{project_id}/secrets/{name}/versions/{version}"

    # Access the secret version.
    response = client.access_secret_version(request={"name": name})

    # Verify payload checksum.
    crc32c = google_crc32c.Checksum()
    crc32c.update(response.payload.data)
    if response.payload.data_crc32c != int(crc32c.hexdigest(), 16):
        raise ValueError(
            f"Data corruption detected when checking out credentials from secret manager (secret: '{name}')."
        )

    # Print the secret payload.
    #
    # WARNING: Do not print the secret in a production environment - this
    # snippet is showing how to access the secret material.

    if return_type == SecretReturnType.JSON_OBJECT:
        payload = json.loads(response.payload.data.decode("UTF-8"))
    elif return_type == SecretReturnType.STRING:
        payload = response.payload.data.decode("UTF-8")
    else:  # BYTES: default
        payload = response.payload.data
    # default: per il momento bytes, poi vediamo
    return payload
    # Handle the response