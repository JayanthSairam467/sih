"""Demo API routes — serves pre-built real-world incident data."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.models.schemas import IncidentInfo, IncidentResponse
from app.services.demo_data import INCIDENTS, INCIDENT_BUILDERS
from app.api.attribution import set_tracks

router = APIRouter()


@router.get("/incidents")
async def list_incidents():
    """List available demo incidents."""
    return {"incidents": list(INCIDENTS.values())}


@router.get("/incidents/{incident_id}", response_model=IncidentResponse)
async def get_incident(incident_id: str):
    """
    Get full incident data: detection, AIS tracks, attribution, drift.
    Also loads tracks into the attribution engine.
    """
    if incident_id not in INCIDENT_BUILDERS:
        return JSONResponse(
            status_code=404,
            content={"error": f"Incident '{incident_id}' not found. Available: {list(INCIDENT_BUILDERS.keys())}"},
        )

    response = INCIDENT_BUILDERS[incident_id]()

    # Load tracks into attribution engine so subsequent /api/attribution/score calls work
    set_tracks(response.vessel_tracks)

    return response
