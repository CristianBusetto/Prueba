from fastapi import APIRouter, HTTPException, Query
from azure.devops.v7_1.work_item_tracking.models import JsonPatchOperation, Wiql
from dependencies import get_devops_connection
from config import AZURE_ORGANIZATION
from schemas import CreateTaskRequest, UpdateWorkItemRequest

router = APIRouter(tags=["Work Items"])

WI_FIELDS = [
    "System.Id",
    "System.Title",
    "System.State",
    "Microsoft.VSTS.Scheduling.CompletedWork",
    "Custom.UN",
    "Custom.Tipo",
]


def serialize_workitem(wi) -> dict:
    f = wi.fields
    return {
        "id": f.get("System.Id"),
        "title": f.get("System.Title"),
        "state": f.get("System.State"),
        "completed_work": f.get("Microsoft.VSTS.Scheduling.CompletedWork"),
        "un": f.get("Custom.UN"),
        "tipo": f.get("Custom.Tipo"),
    }


@router.get(
    "/projects/{project}/workitems",
    summary="Buscar work items por usuario y/o sprint",
    description=(
        "Busca Tasks dentro del proyecto filtrando opcionalmente por usuario asignado y sprint. "
        "Retorna id, título, estado y horas completadas (Completed Work)."
    ),
)
def get_workitems(
    project: str,
    user: str = Query(None, description="Email o nombre del usuario asignado (AssignedTo)."),
    sprint: str = Query(None, description="Nombre del sprint o ruta completa (ej: 'Sprint 5' o 'MiProyecto\\\\Sprint 5')."),
    top: int = Query(200, ge=1, le=1000, description="Cantidad máxima de work items a retornar."),
):
    conditions = [
        f"[System.TeamProject] = '{project}'",
        "[System.WorkItemType] = 'Task'",
        "[System.State] <> 'Removed'",
    ]

    if user:
        conditions.append(f"[System.AssignedTo] = '{user}'")

    if sprint:
        iteration_path = sprint if "\\" in sprint else f"{project}\\{sprint}"
        conditions.append(f"[System.IterationPath] = '{iteration_path}'")

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
        return {"project": project, "filters": {"user": user, "sprint": sprint}, "count": 0, "work_items": []}

    try:
        work_items = wit_client.get_work_items(ids=ids, fields=WI_FIELDS, error_policy="omit")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al obtener work items: {str(e)}")

    return {
        "project": project,
        "filters": {"user": user, "sprint": sprint},
        "count": len(work_items),
        "work_items": [serialize_workitem(wi) for wi in work_items],
    }


@router.post(
    "/projects/{project}/userstories/{userstory_id}/tasks",
    summary="Crear una task dentro de una User Story",
    description="Crea una nueva Task vinculada como hija de la User Story indicada.",
    status_code=201,
)
def create_task(project: str, userstory_id: int, body: CreateTaskRequest):
    organization_url = f"https://dev.azure.com/{AZURE_ORGANIZATION}"

    patch_document = [
        JsonPatchOperation(op="add", path="/fields/System.Title", value=body.title),
        JsonPatchOperation(
            op="add",
            path="/relations/-",
            value={
                "rel": "System.LinkTypes.Hierarchy-Reverse",
                "url": f"{organization_url}/{project}/_apis/wit/workItems/{userstory_id}",
                "attributes": {"comment": ""},
            },
        ),
    ]

    if body.iteration:
        iteration_path = body.iteration if "\\" in body.iteration else f"{project}\\{body.iteration}"
    else:
        iteration_path = None

    optional_fields = {
        "System.State": body.state,
        "Custom.Tipo": body.tipo,
        "Custom.UN": body.un,
        "Microsoft.VSTS.Scheduling.CompletedWork": body.completed_work,
        "System.AssignedTo": body.assigned_to,
        "System.IterationPath": iteration_path,
    }
    for ref, value in optional_fields.items():
        if value is not None:
            patch_document.append(JsonPatchOperation(op="add", path=f"/fields/{ref}", value=value))

    try:
        connection = get_devops_connection()
        wit_client = connection.clients.get_work_item_tracking_client()
        created = wit_client.create_work_item(document=patch_document, project=project, type="Task")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al crear la task: {str(e)}")

    return {"userstory_id": userstory_id, "task": serialize_workitem(created)}


@router.patch(
    "/projects/{project}/workitems/{workitem_id}",
    summary="Actualizar una task",
    description="Actualiza uno o más campos de una task: título, estado, tipo, UN y/o horas completadas.",
)
def update_workitem(project: str, workitem_id: int, body: UpdateWorkItemRequest):
    field_map = {
        "System.Title": body.title,
        "System.State": body.state,
        "Custom.Tipo": body.tipo,
        "Custom.UN": body.un,
        "Microsoft.VSTS.Scheduling.CompletedWork": body.completed_work,
    }

    patch_document = [
        JsonPatchOperation(op="add", path=f"/fields/{ref}", value=value)
        for ref, value in field_map.items()
        if value is not None
    ]

    if not patch_document:
        raise HTTPException(status_code=422, detail="Debe enviar al menos un campo para actualizar")

    try:
        connection = get_devops_connection()
        wit_client = connection.clients.get_work_item_tracking_client()
        updated = wit_client.update_work_item(document=patch_document, id=workitem_id, project=project)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al actualizar el work item: {str(e)}")

    return serialize_workitem(updated)
