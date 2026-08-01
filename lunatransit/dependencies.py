import folium
from fastapi import Request


def get_folium_map(request: Request) -> folium.Map:
    """
    Returns folium.Map Object
    """
    return request.app.state.map
