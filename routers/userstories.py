from fastapi import APIRouter, HTTPException, Query
from azure.devops.v7_1.work_item_tracking.models import Wiql
from dependencies import get_devops_connection

router = APIRouter(tags=["User Stories"])

US_FIELDS = [
    "System.Id",
    "System.Title",
    "System.State",
    "System.AssignedTo",
    "Microsoft.VSTS.Scheduling.StoryPoints",
]


def serialize_userstory(wi) -> dict:
    f = wi.fields
    assigned = f.get("System.AssignedTo")
    return {
        "id": f.get("System.Id"),
        "title": f.get("System.Title"),
        "state": f.get("System.State"),
        "assigned_to": assigned.get("displayName") if isinstance(assigned, dict) else assigned,
        "story_points": f.get("Microsoft.VSTS.Scheduling.StoryPoints"),
    }


@router.get(
    "/projects/{project}/userstories",
    summary="Buscar User Stories por sprint y proyecto",
    description="Devuelve las User Stories del sprint indicado dentro del proyecto, con filtro opcional por usuario asignado.",
)
def get_userstories(
    project: str,
    sprint: str = Query(..., description="Nombre del sprint o ruta completa (ej: 'Sprint 5' o 'MiProyecto\\\\Sprint 5')."),
    user: str = Query(None, description="Email o nombre del usuario asignado (opcional)."),
    top: int = Query(200, ge=1, le=1000, description="Cantidad máxima de resultados."),
):
    iteration_path = sprint if "\\" in sprint else f"{project}\\{sprint}"

    conditions = [
        f"[System.TeamProject] = '{project}'",
        "[System.WorkItemType] = 'User Story'",
        "[System.State] <> 'Removed'",
        f"[System.IterationPath] = '{iteration_path}'",
    ]

    if user:
        conditions.append(f"[System.AssignedTo] = '{user}'")

    wiql_query = (
        f"SELECT [System.Id] FROM WorkItems "
        f"WHERE {' AND '.join(conditions)} "
        f"ORDER BY [System.Id] ASC"
    )

    try:
        connection = get_devops_connection()
        wit_client = connection.clients.get_work_item_tracking_client()
        result = wit_client.query_by_wiql(Wiql(query=wiql_query), top=top)
        ids = [item.id for item in (result.work_items or [])]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al ejecutar la consulta WIQL: {str(e)}")

    if not ids:
        return {"project": project, "filters": {"sprint": sprint, "user": user}, "count": 0, "user_stories": []}

    try:
        items = wit_client.get_work_items(ids=ids, fields=US_FIELDS, error_policy="omit")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al obtener User Stories: {str(e)}")

    return {
        "project": project,
        "filters": {"sprint": sprint, "user": user},
        "count": len(items),
        "user_stories": [serialize_userstory(wi) for wi in items],
    }
