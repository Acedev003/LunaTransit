import datetime
from enum import Enum
from dataclasses import dataclass
from pydantic import BaseModel, Field

class TransitTarget(str,Enum):
    MOON = "moon"
    SUN  = "sun"

class CalculationRequest(BaseModel):
    callsign: str
    probe_delay: float = Field(gt=0, description="Probe delay in mins")
    transit_target: TransitTarget
    track_len: int = Field(gt=0, description="Track Len in meters")
    track_delta: float
    debug_offset: float = 0.0

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

@dataclass
class TargetShadowPoint:
    time : datetime.datetime
    lat  : float
    lon  : float
    alt  : float
    size : float
