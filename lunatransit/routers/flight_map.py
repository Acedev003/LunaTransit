from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from folium import Map

from ..dependencies import get_folium_map, create_fresh_map

router = APIRouter(prefix="/map")

def generate_html(flight_map: Map) -> HTMLResponse:
    flight_map.get_root().render()
    header    = flight_map.get_root().header.render()
    body_html = flight_map.get_root().html.render()
    script    = flight_map.get_root().script.render()

    html_content = f"""
            <!DOCTYPE html>
            <html>
                <head>
                    {header}
                </head>
                <body>
                    {body_html}
                    <script>
                        {script}
                    </script>
                </body>
            </html>
    """
    return HTMLResponse(content=html_content, status_code=200)

@router.get("/")
async def generate_flight_map(flight_map: Map = Depends(get_folium_map)):
    return generate_html(flight_map)

@router.get("/reset")
async def reset_flight_map(request: Request):
    # Create a completely fresh Map object and assign it to app state
    new_map = create_fresh_map()
    request.app.state.map = new_map

    return generate_html(new_map)