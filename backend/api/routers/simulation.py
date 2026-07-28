from fastapi import APIRouter, HTTPException

from api.deps import db_dependency, user_dependency
from api.schemas.simulation import SimulationRunResponse
from api.services import SimulationService


router = APIRouter(prefix="/simulation", tags=["simulation"])
simulation_service = SimulationService()


@router.post("/run-once", response_model=SimulationRunResponse)
def run_simulation_once(db: db_dependency, user: user_dependency):
    try:
        return simulation_service.run_once(
            db=db,
            user_id=user.get("id"),
        )
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
