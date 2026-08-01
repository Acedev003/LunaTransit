import asyncio
from fastapi import APIRouter, HTTPException, Request, status

from ..schemas import CalculationRequest, TransitTarget
from ..services.transitcalc import calculate

router = APIRouter(prefix="/calc")


@router.post("/", status_code=status.HTTP_202_ACCEPTED)
async def start_calculation(
    calc_request: CalculationRequest,
    request: Request
):
    task: asyncio.Task | None = request.app.state.calc_task

    # Check if a task is currently running
    if task and not task.done():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Job is already running"
        )

    # Determine ephemeris target
    if calc_request.transit_target == TransitTarget.MOON:
        target_eph = request.app.state.moon_eph
    elif calc_request.transit_target == TransitTarget.SUN:
        target_eph = request.app.state.sun_eph
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid transit target specified"
        )

    # Run calculate in a background worker thread
    request.app.state.calc_task = asyncio.create_task(
        asyncio.to_thread(
            calculate,
            calc_request,
            request.app.state.geod,
            request.app.state.fr24client,
            request.app.state.map,
            target_eph,
            request.app.state.earth_eph,
            request.app.state.timescale,
        )
    )

    return {"status": "started"}


@router.post("/interrupt", status_code=status.HTTP_200_OK)
async def interrupt(request: Request):
    task: asyncio.Task | None = request.app.state.calc_task

    if task and not task.done():
        task.cancel()
        request.app.state.calc_task = None
        return {"status": "interrupted"}

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="No calculation is currently running"
    )


@router.get("/poll", status_code=status.HTTP_200_OK)
async def poll_status(request: Request):
    task: asyncio.Task | None = request.app.state.calc_task

    if task is None:
        return {"status": "idle"}
    elif not task.done():
        return {"status": "running"}
    else:
        # Check if thread raised an unhandled exception
        if task.cancelled():
            return {"status": "interrupted"}
        
        exc = task.exception()
        if exc:
            return {"status": "failed", "error": str(exc)}

        return {"status": "completed"}