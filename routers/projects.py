from fastapi import APIRouter, HTTPException, Query
from dependencies import get_devops_connection
from config import AZURE_ORGANIZATION

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.get(
    "",
    summary="Obtener proyectos de la organización",
    description="Devuelve la lista de proyectos de la organización configurada en el servidor.",
)
def get_projects(
    skip: int = Query(0, ge=0, description="Número de proyectos a saltar (paginación)"),
    top: int = Query(100, ge=1, le=1000, description="Cantidad máxima de proyectos a retornar"),
):
    try:
        connection = get_devops_connection()
        core_client = connection.clients.get_core_client()
        projects = core_client.get_projects(skip=skip, top=top)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al conectar con Azure DevOps: {str(e)}")

    return {
        "organization": AZURE_ORGANIZATION,
        "organization_url": f"https://dev.azure.com/{AZURE_ORGANIZATION}",
        "count": len(projects),
        "projects": [
            {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "state": p.state,
                "visibility": p.visibility,
                "last_update_time": p.last_update_time.isoformat() if p.last_update_time else None,
                "url": p.url,
            }
            for p in projects
        ],
    }
