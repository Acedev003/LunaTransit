import folium

from ..schemas import FlightWaypoint, TargetShadowPoint

def render_map(
    map_obj: folium.Map,
    waypoints: list[FlightWaypoint],
    moon_shadows: list[TargetShadowPoint | None] | None = None
) -> folium.Map:
    # 1. Clear existing layers/markers from the map object before re-rendering
    map_obj.objects = {}
    map_obj._children = {}

    if not waypoints:
        return map_obj

    # 2. Extract flight path coordinates and draw flight PolyLine
    flight_coords = [[wp.lat, wp.lon] for wp in waypoints]
    folium.PolyLine(
        locations=flight_coords,
        color="blue",
        weight=3,
        opacity=0.7
    ).add_to(map_obj)

    # 3. Add flight waypoint markers
    for wp in waypoints:
        popup_text = f"Time: {wp.time.strftime('%Y-%m-%d %H:%M:%S')}<br>Link: https://maps.google.com/?q={wp.lat},{wp.lon}"
        folium.CircleMarker(
            location=[wp.lat, wp.lon],
            popup=folium.Popup(html=popup_text),
            radius=5,
            fill=True,
            color="Red",
            fill_color="red"
        ).add_to(map_obj)

    # 4. Handle moon shadow points and lines
    if moon_shadows is not None:
        valid_shadow_coords = []

        for wp, shadow in zip(waypoints, moon_shadows):
            if shadow is None:
                continue

            shadow_lat, shadow_lon = shadow.lat, shadow.lon
            valid_shadow_coords.append([shadow_lat, shadow_lon])

            # Popup for moon shadow point
            popup_text = f"Moon shadow @ {wp.time.strftime('%Y-%m-%d %H:%M:%S')}<br>Link: https://maps.google.com/?q={shadow_lat},{shadow_lon}"
            folium.CircleMarker(
                location=[shadow_lat, shadow_lon],
                popup=folium.Popup(html=popup_text),
                radius=5,
                fill=True,
                color="Purple",
                fill_color="purple"
            ).add_to(map_obj)

            # Dashed line connecting flight position to its corresponding moon shadow point
            folium.PolyLine(
                locations=[[wp.lat, wp.lon], [shadow_lat, shadow_lon]],
                color="gray",
                weight=1,
                opacity=0.5,
                dash_array="5,5"
            ).add_to(map_obj)

        # 5. Draw connecting line along all sequential moon shadow points
        if len(valid_shadow_coords) > 1:
            folium.PolyLine(
                locations=valid_shadow_coords,
                color="purple",
                weight=2,
                opacity=0.8
            ).add_to(map_obj)

    return map_obj