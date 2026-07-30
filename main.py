import os
import math
import folium
import datetime
import webbrowser

from dataclasses import dataclass

from skyfield.api import load, wgs84
from geographiclib.geodesic import Geodesic

from decode_frdump import decode_frdump

@dataclass
class Waypoint:
    time: datetime.time
    lat : float
    lon : float
    alt : float
    azi : float

def get_timed_waypoints(
        start_lat: float,
        start_lon: float, 
        alt: float,
        azi: int,
        speed: float,
        start_time: datetime.datetime, 
        geod: Geodesic, 
        track_len: int = 2000e3, 
        time_delta: int = 5*60) -> list[Waypoint]:

    time_waypoint_data = []
    time_waypoint_data.append(
        Waypoint(
            time = start_time,
            lat  = start_lat,
            lon  = start_lon,
            alt  = alt,
            azi  = azi
        )
    )
    
    g = geod.Direct(start_lat, start_lon, azi, track_len)

    end_lat = g['lat2']
    end_lon = g['lon2']

    line = geod.InverseLine(start_lat,start_lon,end_lat, end_lon)
    ds = 0
    current_time = start_time
    while ds < track_len:
        ds += speed * time_delta
        g = line.Position(ds, Geodesic.STANDARD | Geodesic.LONG_UNROLL)

        current_time += datetime.timedelta(seconds=time_delta)

        time_waypoint_data.append(
            Waypoint(
                time = current_time,
                lat  = g['lat2'],
                lon  = g['lon2'],
                alt  = alt, 
                azi  = g['azi2']
            )
        )
        #print("{:.0f} {:.5f} {:.5f} {:.5f}".format(g['s12'], g['lat2'], g['lon2'], g['azi2']))

    return time_waypoint_data

def render_map(waypoints: list[Waypoint], moon_shadows: list[tuple[float, float] | None] = None,
               file_name: str = "map.html"):
    # 1. Initialize map at the first waypoint
    map_obj = folium.Map(location=[waypoints[0].lat, waypoints[0].lon], zoom_start=12)

    # 2. Extract coordinates sequentially for the flight-path line
    line_coordinates = [[point.lat, point.lon] for point in waypoints]

    # 3. Draw the connecting flight-path line
    folium.PolyLine(
        locations=line_coordinates,
        color="blue",
        weight=3,
        opacity=0.7
    ).add_to(map_obj)

    # 4. Add individual plane-position markers
    for point in waypoints:
        popup_text = f"Time: {point.time.strftime('%Y-%m-%d %H:%M:%S')}\nLink: https://maps.google.com/?q={point.lat},{point.lon}"
        folium.CircleMarker(
            location=[point.lat, point.lon],
            popup=popup_text,
            radius=5,
            fill=True,
            color="Red",
            fill_color="red"
        ).add_to(map_obj)

    # 5. Add moon-shadow markers + a connecting line to each plane position
    if moon_shadows is not None:
        for point, shadow in zip(waypoints, moon_shadows):
            if shadow is None:
                continue  # no valid shadow point at this waypoint (moon below horizon / horizon-dip limit)

            shadow_lat, shadow_lon = shadow

            popup_text = f"Moon shadow @ {point.time.strftime('%Y-%m-%d %H:%M:%S')} <br>  Link: https://maps.google.com/?q={shadow_lat},{shadow_lon}"
            folium.CircleMarker(
                location=[shadow_lat, shadow_lon],
                popup=folium.Popup(
                    html=popup_text
                ),
                radius=5,
                fill=True,
                color="Purple",
                fill_color="purple"
            ).add_to(map_obj)

            # line connecting the plane position to its moon-shadow ground point
            folium.PolyLine(
                locations=[[point.lat, point.lon], [shadow_lat, shadow_lon]],
                color="gray",
                weight=1,
                opacity=0.5,
                dash_array="5,5"
            ).add_to(map_obj)

    # 6. Save and open
    map_obj.save(file_name)
    webbrowser.open_new_tab(f"http://localhost:8000/{file_name}")

def precise_track(geod, lat1, lon1, lat2, lon2):
    g = geod.Inverse(lat1, lon1, lat2, lon2)
    return g['azi2'] % 360

def exact_geocentric_arc(h: float, elevation_deg: float, R_EARTH: int) -> float | None:
    """
    Exact horizontal arc distance (spherical Earth) from the plane's
    sub-point to the Moon-line's ground intersection. Returns None if
    elevation is below the horizon-dip limit for this altitude.
    """
    alpha = math.radians(elevation_deg)
    val = (R_EARTH + h) * math.cos(alpha) / R_EARTH
    if val > 1.0:
        return None
    beta = math.asin(val)
    theta = 180 * math.pi/180 - (90 * math.pi/180 - alpha + (180 * math.pi/180 - beta))
    return R_EARTH * theta

def moon_shadow_point(plane_lat: float, plane_lon: float, plane_alt_m: float,dt_utc, moon, earth, ts, geod) -> tuple[float, float] | None:
    """
    Ground point where a straight line from the Moon through the plane
    hits Earth's surface -- i.e. where an observer would see the plane
    transit the Moon's disc.

    Uses Skyfield for topocentric az/el (handles lunar parallax correctly),
    the exact spherical geocentric-angle formula for the horizontal offset
    (instead of the flat h/tan(e) approximation), and geographiclib to walk
    that offset along the true WGS84 ellipsoid surface.

    dt_utc must be a timezone-aware UTC datetime.

    Returns None if:
      - the Moon is below the horizon at the plane's position, or
      - elevation is below the horizon-dip limit for this altitude
        (near-horizon transit -- exact-sphere formula breaks down; you'd
        need the full 3D ray-ellipsoid intersection for that case).
    """

    t = ts.from_datetime(dt_utc)

    observer = earth + wgs84.latlon(plane_lat, plane_lon, elevation_m=plane_alt_m)
    astrometric = observer.at(t).observe(moon)
    alt, az, distance = astrometric.apparent().altaz()

    moon_el = alt.degrees
    moon_az = az.degrees

    if moon_el <= 0:
        return None  # moon below horizon at the plane's location

    horiz_offset = exact_geocentric_arc(plane_alt_m, moon_el, wgs84.radius.m)
    if horiz_offset is None:
        return None  # below horizon-dip limit -- needs full ray-ellipsoid solver

    away_azimuth = (moon_az + 180) % 360
    g = geod.Direct(plane_lat, plane_lon, away_azimuth, horiz_offset)

    return g['lat2'], g['lon2']

def main():
    geod = Geodesic.WGS84
    eph  = load('de421.bsp')
    ts   = load.timescale()

    sun, moon, earth = eph['sun'], eph['moon'], eph['earth']

    with open('data_pair.b64','r') as f:
        DUMP_DAT1, DUMP_DAT2 = f.readlines()

    fr_list1 = decode_frdump(DUMP_DAT1)
    fr_data1 = fr_list1[-1]

    fr_list2 = decode_frdump(DUMP_DAT2)
    fr_data2 = fr_list2[-1]

    azi = precise_track(geod, fr_data1.lat, fr_data1.lon, fr_data2.lat, fr_data2.lon)
    print(azi, fr_data2.track)
    #exit()
    fr_data = fr_data2
    start_time = datetime.datetime.fromtimestamp(fr_data.utc)  # local time, naive

    res = get_timed_waypoints(
        fr_data.lat, 
        fr_data.lon, 
        fr_data.baro_alt_m,
        azi, 
        fr_data.gnd_speed_ms, 
        start_time, 
        geod,
        track_len=2000e3,
        time_delta=0.5*60
    )

    moon_shadows = []
    for x in res:
        time_observe = x.time.astimezone(datetime.timezone.utc) #+ datetime.timedelta(hours=2)
        moon_shadows.append(
            moon_shadow_point(
                x.lat,
                x.lon,
                x.alt,
                time_observe,
                moon,
                earth,
                ts,
                geod
            )
        )

    render_map(res, moon_shadows)

if __name__ == "__main__":
    main()