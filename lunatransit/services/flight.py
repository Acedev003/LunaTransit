"""
Flight Prediction and calculations
"""

import time
import datetime

from fr24sdk.client import Client as FR24Client
from geographiclib.geodesic import Geodesic

from ..schemas import FlightWaypoint

def estimate_flight_track_fr(
        callsign: str,
        delay_seconds: int,
        geod: Geodesic,
        client: FR24Client
    ) -> FlightWaypoint:
    """
    Calculate precise track of aircraft from 2 position fixes.
    """
    pos1 = client.live.flight_positions.get_light(callsigns=[callsign]).data[-1]
    time.sleep(delay_seconds)
    pos2 = client.live.flight_positions.get_light(callsigns=[callsign]).data[-1]

    pos = geod.Inverse(pos1.lat, pos1.lon, pos2.lat,pos2.lon)
    azi = pos['azi2'] % 360

    dt_utc = datetime.datetime.fromisoformat(pos2.timestamp)
    altm   = pos2.alt * 0.3048
    speedm = pos2.gspeed * 0.514444

    return FlightWaypoint(
        time  = dt_utc,
        lat   = pos2.lat,
        lon   = pos2.lon,
        alt   = altm,
        azi   = azi,
        speed = speedm
    )

def get_timed_waypoints(
        start_waypoint: FlightWaypoint,
        geod: Geodesic,
        track_len: int  = 2000e3,
        time_delta: int = 0.5 *60
    ) -> list[FlightWaypoint]:
    """
    Calculate estimated waypoints for an aircraft given starting conditions.

    :param track_len: Waypoint calculation distance in meters
    :param time_delta: Time gap btw waypoints in seconds
    """

    start_lat = start_waypoint.lat
    start_lon = start_waypoint.lon
    start_alt = start_waypoint.alt
    start_azi = start_waypoint.azi
    start_time  = start_waypoint.time
    start_speed = start_waypoint.speed

    waypoint_data = []
    waypoint_data.append(
        FlightWaypoint(
            time = start_time,
            lat  = start_lat,
            lon  = start_lon,
            alt  = start_alt,
            azi  = start_azi,
            speed = start_speed
        )
    )

    g = geod.Direct(start_lat, start_lon, start_azi, track_len)

    end_lat = g['lat2']
    end_lon = g['lon2']

    flight_path = geod.InverseLine(start_lat,start_lon,end_lat, end_lon)

    ds = 0
    current_time = start_time

    while ds < track_len:
        ds += start_speed * time_delta
        pos = flight_path.Position(ds, Geodesic.STANDARD | Geodesic.LONG_UNROLL)

        current_time += datetime.timedelta(seconds=time_delta)

        waypoint_data.append(
            FlightWaypoint(
                time = current_time,
                lat  = pos['lat2'],
                lon  = pos['lon2'],
                alt  = start_alt,
                azi  = pos['azi2'],
                speed = start_speed
            )
        )

    return waypoint_data
