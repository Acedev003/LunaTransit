import folium
from fastapi import Request
from .config import settings

def create_fresh_map() -> folium.Map:
    """Helper to generate a clean, unrendered Folium Map instance."""
    return folium.Map(
        location=[settings.init_lat, settings.init_lon],
        zoom_start=settings.init_zoom_level
    )

def get_folium_map(request: Request) -> folium.Map:
    """
    Returns the current folium.Map Object from app state.
    """
    return request.app.state.map