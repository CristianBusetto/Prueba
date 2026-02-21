from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from azure.devops.v7_1.work.models import TeamContext
from dependencies import get_devops_connection

router = APIRouter(tags=["Sprints"])


def serialize_sprint(iteration) -> dict:
    attrs = iteration.attributes
    return {
        "id": iteration.id,
        "name": iteration.name,
        "path": iteration.path,
        "start_date": attrs.start_date.isoformat() if attrs and attrs.start_date else None,
        "finish_date": attrs.finish_date.isoformat() if attrs and attrs.finish_date else None,
        "time_frame": attrs.time_frame if attrs else None,
        "url": iteration.url,
    }


@router.get(
    "/projects/{project}/sprints",
    summary="Obtener todos los sprints de un proyecto",
    description="Devuelve los sprints del team especificado, ordenados del más reciente al más antiguo.",
)
def get_sprints(
    project: str,
    team: str = Query(None, description="Nombre del team. Si no se indica, usa el team por defecto del proyecto."),
    top: int = Query(None, ge=1, description="Cantidad máxima de sprints a retornar. Si no se indica, devuelve todos."),
):
    team_name = team or f"{project} Team"
    team_context = TeamContext(project=project, team=team_name)
    try:
        connection = get_devops_connection()
        work_client = connection.clients.get_work_client()
        iterations = work_client.get_team_iterations(team_context)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al obtener sprints: {str(e)}")

    sorted_iterations = sorted(
        iterations,
        key=lambda i: (i.attributes.start_date or datetime.min) if i.attributes else datetime.min,
        reverse=True,
    )

    if top is not None:
        sorted_iterations = sorted_iterations[:top]

    return {
        "project": project,
        "team": team_name,
        "count": len(sorted_iterations),
        "sprints": [serialize_sprint(i) for i in sorted_iterations],
    }


@router.get(
    "/projects/{project}/sprints/current",
    summary="Obtener el sprint actual de un proyecto",
    description="Devuelve el sprint en curso (timeframe=current) del team especificado dentro del proyecto.",
)
def get_current_sprint(
    project: str,
    team: str = Query(None, description="Nombre del team. Si no se indica, usa el team por defecto del proyecto."),
):
    team_name = team or f"{project} Team"
    team_context = TeamContext(project=project, team=team_name)
    try:
        connection = get_devops_connection()
        work_client = connection.clients.get_work_client()
        iterations = work_client.get_team_iterations(team_context, timeframe="current")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al obtener sprint actual: {str(e)}")

    if not iterations:
        raise HTTPException(status_code=404, detail="No hay sprint activo para este proyecto/team")

    return {
        "project": project,
        "team": team_name,
        "current_sprint": serialize_sprint(iterations[0]),
    }
