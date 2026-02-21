from azure.devops.connection import Connection
from msrest.authentication import BasicAuthentication
from config import AZURE_PAT, AZURE_ORGANIZATION


def get_devops_connection() -> Connection:
    credentials = BasicAuthentication("", AZURE_PAT)
    organization_url = f"https://dev.azure.com/{AZURE_ORGANIZATION}"
    return Connection(base_url=organization_url, creds=credentials)
