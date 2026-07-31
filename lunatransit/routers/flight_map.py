from folium import Map
from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse

from ..dependencies import get_folium_map

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
    return HTMLResponse(content=html_content,status_code=200)

@router.get("/")
async def generate_flight_map(flight_map: Map = Depends(get_folium_map)):
    return generate_html(flight_map)