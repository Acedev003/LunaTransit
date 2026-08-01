import math
import datetime
import traceback

import srtm

from folium import Map
from fastapi import Request
from skyfield.api import wgs84, Distance
from skyfield.timelib import Timescale
from global_land_mask import globe
from fr24sdk.client import Client
from geographiclib.geodesic import Geodesic

from ..schemas import CalculationRequest, FlightWaypoint, TargetShadowPoint
from .flight import estimate_flight_track_fr, get_timed_waypoints
from .map import render_map

def is_or_near_land(lat: float, lon: float, delta_deg: float = 2) -> bool:
    if globe.is_land(lat,lon):
        return True

    neighbours = [
        (lat + delta_deg, lon),
        (lat - delta_deg, lon),
        (lat, lon + delta_deg),
        (lat, lon - delta_deg),
    ]

    return any(globe.is_land(n_lat,n_lon) for n_lat, n_lon in neighbours)

def filter_nearland_waypoints(waypoints: list[FlightWaypoint]) -> list[FlightWaypoint]:
    filtered_waypoints = [x for x in waypoints if is_or_near_land(x.lat,x.lon)]
    return filtered_waypoints

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
    #theta = 180 * math.pi/180 - (90 * math.pi/180 - alpha + (180 * math.pi/180 - beta))
    theta = alpha + beta - (math.pi / 2)
    return R_EARTH * theta

def safe_get_elevation(lat: float, lon: float, elevation_data: srtm.mod_main.mod_data.GeoElevationData) -> float:
    try:
        alt = elevation_data.get_elevation(lat, lon)
        return float(alt) if alt is not None else 0.0
    except Exception as e:
        print(f"SRTM lookup error at ({lat}, {lon}): {e}")
        return 0.0

def calc_shadow_point(
        plane_lat: float,
        plane_lon: float,
        plane_alt: float,
        target_eph,
        earth_eph,
        date_utc: datetime.datetime,
        timescale: Timescale,
        wgs84_geod: Geodesic,
        elevation_data: srtm.mod_main.mod_data.GeoElevationData
    ) -> TargetShadowPoint | None:

    observation_time = timescale.from_datetime(date_utc)

    observer = earth_eph + wgs84.latlon(plane_lat, plane_lon, elevation_m=plane_alt)
    astrometric = observer.at(observation_time).observe(target_eph)
    alt, az, distance = astrometric.apparent().altaz()

    moon_el = alt.degrees
    moon_az = az.degrees

    if moon_el <= 0:
        return None  # moon below horizon at the plane's location

    horiz_offset = exact_geocentric_arc(plane_alt, moon_el, wgs84.radius.m)
    if horiz_offset is None:
        return None  # below horizon-dip limit

    away_azimuth = (moon_az + 180) % 360
    g = wgs84_geod.Direct(plane_lat, plane_lon, away_azimuth, horiz_offset)

    observer_lat = g['lat2']
    observer_lon = g['lon2']
    observer_alt = safe_get_elevation(observer_lat,observer_lon,elevation_data)

    point_A = wgs84.latlon(
                    latitude_degrees=observer_lat,
                    longitude_degrees=observer_lon,
                    elevation_m=observer_alt,
              ).at(observation_time).position.m
    point_B = wgs84.latlon(
                    latitude_degrees=plane_lat,
                    longitude_degrees=plane_lon,
                    elevation_m=plane_alt,
              ).at(observation_time).position.m

    ray_vector = point_B - point_A
    vec_magnitude = (ray_vector ** 2).sum() ** 0.5
    distance_m = Distance(m=vec_magnitude).m
    approx_targ_size = distance_m / 100.0

    return TargetShadowPoint(
        time = date_utc,
        lat  = observer_lat,
        lon  = observer_lon,
        alt  = observer_alt,
        size = approx_targ_size
    )

def calculate(
        request: Request,
        calc_request_data: CalculationRequest,
        wgs84_geod: Geodesic,
        fr_client: Client,
        target_eph,
        earth_eph,
        timescale: Timescale,
        elevation_data: srtm.mod_main.mod_data.GeoElevationData
    ) -> None:
    
    callsign    = calc_request_data.callsign
    probe_delay = int(calc_request_data.probe_delay * 60)
    track_len   = calc_request_data.track_len
    track_delta = int(calc_request_data.track_delta * 60)

    start_waypoint = estimate_flight_track_fr(
                        callsign,
                        probe_delay,
                        wgs84_geod,
                        fr_client
                    )
    
    flight_waypoints  = get_timed_waypoints(
                            start_waypoint,
                            wgs84_geod,
                            track_len,
                            track_delta
                        )

    flight_waypoints_filtered = [flight_waypoints[0]] + filter_nearland_waypoints(flight_waypoints[1:])

    try:
        moon_observation_points = [
        calc_shadow_point(
            waypoint.lat,
            waypoint.lon,
            waypoint.alt,
            target_eph,
            earth_eph,
            waypoint.time,
            timescale,
            wgs84_geod,
            elevation_data
        ) for waypoint in flight_waypoints_filtered
    ]
    except Exception as e:
        print("=" * 60)
        print("ERROR INSIDE SHADOW POINT CALCULATION:")
        traceback.print_exc()  # <--- Prints the exact line & error to standard error
        print("=" * 60)
        raise e

    render_map(request, flight_waypoints_filtered, moon_observation_points)
