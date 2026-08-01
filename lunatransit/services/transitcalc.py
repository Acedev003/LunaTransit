import math
import datetime

from folium import Map
from pyhigh import get_elevation
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

def calc_shadow_point(
        plane_lat: float,
        plane_lon: float,
        plane_alt: float,
        target_eph,
        earth_eph,
        date_utc: datetime.datetime,
        timescale: Timescale,
        wgs84_geod: Geodesic,
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
    observer_alt = get_elevation(observer_lat,observer_lon)
    if observer_alt is None:
        observer_alt = 0.0

    # point_A = wgs84.latlon(
    #                 latitude_degrees=observer_lat,
    #                 longitude_degrees=observer_lon,
    #                 elevation_m=observer_alt,
    #           ).at(observation_time).position.meters
    # point_B = wgs84.latlon(
    #                 latitude_degrees=plane_lat,
    #                 longitude_degrees=plane_lon,
    #                 elevation_m=plane_alt,
    #           ).at(observation_time).position.meters

    # ray_vector = point_B - point_A
    # distance_m = math.sqrt(sum(c**2 for c in ray_vector))
    # approx_targ_size = distance_m / 100.0

    pos_A = wgs84.latlon(
        latitude_degrees=observer_lat,
        longitude_degrees=observer_lon,
        elevation_m=observer_alt,
    ).at(observation_time)

    pos_B = wgs84.latlon(
        latitude_degrees=plane_lat,
        longitude_degrees=plane_lon,
        elevation_m=plane_alt,
    ).at(observation_time)

    # Skyfield subtraction yields a displacement vector object whose distance can be read directly
    distance_m = (pos_B - pos_A).distance().m
    approx_targ_size = distance_m / 100.0

    return TargetShadowPoint(
        time = date_utc,
        lat  = observer_lat,
        lon  = observer_lon,
        alt  = observer_alt,
        size = approx_targ_size
    )

def calculate(
        calc_request_data: CalculationRequest,
        wgs84_geod: Geodesic,
        fr_client: Client,
        folium_map: Map,
        target_eph,
        earth_eph,
        timescale: Timescale
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

    moon_observation_points = [
        calc_shadow_point(
            waypoint.lat,
            waypoint.lon,
            waypoint.alt,
            target_eph,
            earth_eph,
            waypoint.time,
            timescale,
            wgs84_geod
        ) for waypoint in flight_waypoints_filtered
    ]

    render_map(folium_map, flight_waypoints_filtered, moon_observation_points)
