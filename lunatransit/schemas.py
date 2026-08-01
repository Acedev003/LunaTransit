import datetime
from dataclasses import dataclass

@dataclass
class FlightWaypoint:
    """
    Flight Waypoint Data

    Attributes:
        time (datetime.datetime): timestamp of current reading in UTC
        lat  (float): WGS84 lat in degrees 
        lon  (float): WGS84 lon in degrees
        alt  (float): altitude in meters
        azi  (float): track in degrees (0-360)
        speed (float): speed in m/s
    """
    time : datetime.datetime    
    lat  : float                
    lon  : float
    alt  : float
    azi  : float
    speed: float

class MoonShadowPoint:
    time : datetime.datetime
    lat  : float
    lon  : float
