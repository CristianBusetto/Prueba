import os
from dotenv import load_dotenv

load_dotenv()

AZURE_PAT = os.getenv("AZURE_PAT")
AZURE_ORGANIZATION = os.getenv("AZURE_ORGANIZATION")

if not AZURE_PAT or not AZURE_ORGANIZATION:
    raise RuntimeError("Faltan variables de entorno: AZURE_PAT y AZURE_ORGANIZATION son requeridas")


def get_server_url() -> str:
    azure_hostname = os.getenv("WEBSITE_HOSTNAME")
    if azure_hostname:
        return f"https://{azure_hostname}"
    host = os.getenv("HOST", "localhost")
    port = os.getenv("PORT", "8000")
    return f"http://{host}:{port}"
