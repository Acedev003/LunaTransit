import datetime
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


def format_dual_time(dt: datetime.datetime) -> str:
    """
    Formats a datetime object to display both UTC and IST (UTC+5:30).
    Assumes naive datetime is in UTC.
    """
    ist_offset = datetime.timedelta(hours=5, minutes=30)
    ist_dt = dt + ist_offset
    
    utc_str = dt.strftime('%Y-%m-%d %H:%M:%S')
    ist_str = ist_dt.strftime('%Y-%m-%d %H:%M:%S')
    
    return f"<b>UTC:</b> {utc_str}<br><b>IST:</b> {ist_str}"


def render_map(
    request: Request,
    waypoints: list[FlightWaypoint],
    moon_shadows: list[TargetShadowPoint | None] | None = None
) -> folium.Map:
    
    # 1. Instantiate a fresh map instance
    new_map = create_fresh_map()

    if waypoints:
        # Draw flight trajectory
        flight_coords = [[wp.lat, wp.lon] for wp in waypoints]
        folium.PolyLine(
            locations=flight_coords,
            color="blue",
            weight=3,
            opacity=0.7
        ).add_to(new_map)

        # Draw flight waypoint markers
        for wp in waypoints:
            gmaps_url = f"https://maps.google.com/?q={wp.lat},{wp.lon}"
            time_display = format_dual_time(wp.time)
            
            flight_popup_html = f"""
            <div style="font-family: Arial, sans-serif; font-size: 13px; line-height: 1.5; min-width: 220px;">
                <b style="color: #d9534f; font-size: 14px;">✈️ Aircraft Position</b><hr style="margin: 4px 0; border: 0; border-top: 1px solid #ccc;">
                {time_display}<br>
                <b>Lat, Lon:</b> {wp.lat:.5f}, {wp.lon:.5f}<br>
                <div style="margin-top: 6px;">
                    <a href="{gmaps_url}" target="_blank" style="color: #0275d8; text-decoration: none; font-weight: bold;">📍 Open in Google Maps</a>
                </div>
            </div>
            """
            
            folium.CircleMarker(
                location=[wp.lat, wp.lon],
                popup=folium.Popup(html=flight_popup_html, max_width=320),
                radius=5,
                fill=True,
                color="Red",
                fill_color="red"
            ).add_to(new_map)

        all_bounds_coords = list(flight_coords)

        # Draw Moon Shadow / Observer points
        if moon_shadows is not None:
            valid_shadow_coords = []

            for wp, shadow in zip(waypoints, moon_shadows):
                if shadow is None:
                    continue

                shadow_lat, shadow_lon = shadow.lat, shadow.lon
                valid_shadow_coords.append([shadow_lat, shadow_lon])
                all_bounds_coords.append([shadow_lat, shadow_lon])

                gmaps_url = f"https://maps.google.com/?q={shadow_lat},{shadow_lon}"
                time_display = format_dual_time(shadow.time)

                observer_popup_html = f"""
                <div style="font-family: Arial, sans-serif; font-size: 13px; line-height: 1.5; min-width: 240px;">
                    <b style="color: #6f42c1; font-size: 14px;">🌕 Observer Location</b><hr style="margin: 4px 0; border: 0; border-top: 1px solid #ccc;">
                    {time_display}<br>
                    <b>Lat, Lon:</b> {shadow_lat:.5f}, {shadow_lon:.5f}<br>
                    <b>Azimuth / Bearing:</b> {shadow.azi:.2f}°<br>
                    <b>Altitude (Ground):</b> {shadow.alt:.1f} m<br>
                    <b>Size:</b> {shadow.size:.1f} m<br>
                    <div style="margin-top: 6px;">
                        <a href="{gmaps_url}" target="_blank" style="color: #0275d8; text-decoration: none; font-weight: bold;">📍 Open in Google Maps</a>
                    </div>
                </div>
                """

                # Observer point marker
                folium.CircleMarker(
                    location=[shadow_lat, shadow_lon],
                    popup=folium.Popup(html=observer_popup_html, max_width=320),
                    radius=5,
                    fill=True,
                    color="Purple",
                    fill_color="purple"
                ).add_to(new_map)

                # Dotted connector line between aircraft and ground observer location
                folium.PolyLine(
                    locations=[[wp.lat, wp.lon], [shadow_lat, shadow_lon]],
                    color="gray",
                    weight=1,
                    opacity=0.5,
                    dash_array="5,5"
                ).add_to(new_map)

            # Draw ground shadow path trajectory line
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