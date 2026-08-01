"""
App Entrypoint
"""

from contextlib import asynccontextmanager

import folium

from fastapi import FastAPI
from starlette.responses import FileResponse

from skyfield.api import load
from fr24sdk.client import Client
from geographiclib.geodesic import Geodesic

from .routers import flight_map
from .config import settings

@asynccontextmanager
async def lifespan(_app: FastAPI):
    """
    App Lifespan and global dependency management
    """
    _app.state.map  = folium.Map(
                        location=[settings.init_lat, settings.init_lon],
                        zoom_start=settings.init_zoom_level
                      )
    _app.state.geod = Geodesic.WGS84

    ephemeris = load('de421.bsp')

    _app.state.sun_eph    = ephemeris['sun']
    _app.state.earth_eph  = ephemeris['earth']
    _app.state.moon_eph   = ephemeris['moon']
    _app.state.timescale  = load.timescale()

    _app.state.fr24client = Client(api_token=settings.fr24_api_token)

    yield

    _app.state.fr24client.close()

app = FastAPI(lifespan=lifespan)
app.include_router(flight_map.router)

@app.get("/")
async def main():
    return FileResponse("lunatransit/html/index.html")