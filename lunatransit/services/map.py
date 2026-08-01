import folium
from folium import plugins
from fastapi import Request
from ..config import settings
from ..schemas import FlightWaypoint, TargetShadowPoint

def create_fresh_map() -> folium.Map:
    """Core factory function to build an unrendered map with default layers and plugins."""
    flight_map = folium.Map(
        location=[settings.init_lat, settings.init_lon],
        zoom_start=settings.init_zoom_level
    )
    
    # Attach location control plugin
    plugins.LocateControl(auto_start=False).add_to(flight_map)
    
    return flight_map

def render_map(
    request: Request,
    waypoints: list[FlightWaypoint],
    moon_shadows: list[TargetShadowPoint | None] | None = None
) -> folium.Map:
    
    # 1. Instantiate a fresh map instance
    new_map = create_fresh_map()

    if waypoints:
        # Draw flight lines
        flight_coords = [[wp.lat, wp.lon] for wp in waypoints]
        folium.PolyLine(
            locations=flight_coords,
            color="blue",
            weight=3,
            opacity=0.7
        ).add_to(new_map)

        # Draw waypoint markers
        for wp in waypoints:
            popup_text = f"Time: {wp.time.strftime('%Y-%m-%d %H:%M:%S')}<br><a href='https://maps.google.com/?q={wp.lat},{wp.lon}' target='_blank'>Google Maps</a>"
            folium.CircleMarker(
                location=[wp.lat, wp.lon],
                popup=folium.Popup(html=popup_text, max_width=300),
                radius=5,
                fill=True,
                color="Red",
                fill_color="red"
            ).add_to(new_map)

        all_bounds_coords = list(flight_coords)

        if moon_shadows is not None:
            valid_shadow_coords = []

            for wp, shadow in zip(waypoints, moon_shadows):
                if shadow is None:
                    continue

                shadow_lat, shadow_lon = shadow.lat, shadow.lon
                valid_shadow_coords.append([shadow_lat, shadow_lon])
                all_bounds_coords.append([shadow_lat, shadow_lon])

                popup_text = f"Moon shadow @ {wp.time.strftime('%Y-%m-%d %H:%M:%S')}<br><a href='https://maps.google.com/?q={shadow_lat},{shadow_lon}' target='_blank'>Google Maps</a>"
                folium.CircleMarker(
                    location=[shadow_lat, shadow_lon],
                    popup=folium.Popup(html=popup_text, max_width=300),
                    radius=5,
                    fill=True,
                    color="Purple",
                    fill_color="purple"
                ).add_to(new_map)

                folium.PolyLine(
                    locations=[[wp.lat, wp.lon], [shadow_lat, shadow_lon]],
                    color="gray",
                    weight=1,
                    opacity=0.5,
                    dash_array="5,5"
                ).add_to(new_map)

            if len(valid_shadow_coords) > 1:
                folium.PolyLine(
                    locations=valid_shadow_coords,
                    color="purple",
                    weight=2,
                    opacity=0.8
                ).add_to(new_map)

        if all_bounds_coords:
            new_map.fit_bounds(all_bounds_coords)

    # 2. Update the FastAPI application state with the fresh map
    request.app.state.map = new_map
    return new_map