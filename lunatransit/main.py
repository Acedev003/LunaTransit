import folium

from fastapi import FastAPI
from starlette.responses import FileResponse
from contextlib import asynccontextmanager

from .routers import folium_map

@asynccontextmanager
async def lifespan(_app: FastAPI):
    _app.state.map = folium.Map(location=[20.5937, 78.9629],zoom_start=5)
    yield

app = FastAPI(lifespan=lifespan)
app.include_router(folium_map.router)

@app.get("/")
async def main():
    return FileResponse("lunatransit/html/index.html")