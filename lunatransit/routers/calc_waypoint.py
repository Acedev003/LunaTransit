from fastapi import APIRouter, BackgroundTasks

router = APIRouter(prefix="/calc")

def calculate(
        callsign: str,
        probe_delay: float,
        transit_target: str,
        track_len: int,
        track_delta: float,
        debug_offset: float
    ):
    pass


@router.get("/{callsign}/{probe_delay}/{transit_target}/{track_len}/{track_delta}/{debug_offset}")
async def start_calculation(
        callsign: str,
        probe_delay: float,
        transit_target: str,
        track_len: int,
        track_delta: float,
        debug_offset: float,
        background_tasks: BackgroundTasks
    ):
    background_tasks.add_task(
        calculate,
        callsign,
        probe_delay,
        transit_target,
        track_len,
        track_delta,
        debug_offset
    )
    return ""

@router.get("/interrupt")
async def interrupt():
    return ""

@router.get("/poll")
async def poll_status():
    return ""