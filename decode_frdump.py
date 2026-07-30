import base64
import struct
import blackboxprotobuf
from dataclasses import dataclass
from typing import Optional


@dataclass
class FRDump:
    utc: int             # utc timestamp seconds
    lat: float           # latitude
    lon: float           # longitude
    track: float         # track in degrees
    baro_alt_ft: float   # barometric altitude in feet
    baro_alt_m: float    # barometric altitude in meters
    gnd_speed_kts: float # Ground speed in knots
    gnd_speed_ms: float  # Ground speed in meters per second
    callsign: str        # callsign
    flight_no: str       # flight number
    registration: str    # registration
    aircraft_type: str   # aircraft type


def _as_float32(raw_int: int) -> float:
    return struct.unpack(">f", struct.pack(">I", raw_int & 0xFFFFFFFF))[0]


def _clean_bytes(val) -> Optional[str]:
    if val is None:
        return None
    if isinstance(val, bytes):
        return val.decode(errors="replace")
    if isinstance(val, str) and val.startswith("b'") and val.endswith("'"):
        return val[2:-1]
    return str(val)


def _parse_position_block(sub: dict) -> Optional[FRDump]:
    if not isinstance(sub, dict) or "2" not in sub or "3" not in sub:
        return None

    lat = _as_float32(sub["2"])
    lon = _as_float32(sub["3"])
    track = sub.get("4")
    baro_alt_ft = sub.get("5")
    gnd_speed_kts = sub.get("6")
    utc = sub.get("9")
    callsign = _clean_bytes(sub.get("11"))

    flight_no = registration = aircraft_type = None
    route = sub.get("13")
    if isinstance(route, dict):
        flight_no = _clean_bytes(route.get("1"))
        registration = _clean_bytes(route.get("2"))
        aircraft_type = _clean_bytes(route.get("4"))

    return FRDump(
        utc=utc,
        lat=lat,
        lon=lon,
        track=float(track) if track is not None else None,
        baro_alt_ft=float(baro_alt_ft) if baro_alt_ft is not None else None,
        baro_alt_m=(baro_alt_ft * 0.3048) if baro_alt_ft is not None else None,
        gnd_speed_kts=float(gnd_speed_kts) if gnd_speed_kts is not None else None,
        gnd_speed_ms=(gnd_speed_kts * 0.514444) if gnd_speed_kts is not None else None,
        callsign=callsign,
        flight_no=flight_no,
        registration=registration,
        aircraft_type=aircraft_type,
    )


def decode_frdump(b64_str: str) -> FRDump:
    data = base64.b64decode(b64_str)
    results = []
    pos = 0
    while pos < len(data):
        flag = data[pos]
        length = struct.unpack(">I", data[pos + 1:pos + 5])[0]
        payload = data[pos + 5:pos + 5 + length]

        if flag & 0x80:
            #print(payload.decode(errors="replace"))
            ...
        else:
            msg, typedef = blackboxprotobuf.decode_message(payload)
            #print(msg)
            for key in ("1", "3"):
                dump = _parse_position_block(msg.get(key))
                if dump is not None:
                    results.append(dump)

        pos += 5 + length
    return results


if __name__ == "__main__":
    with open("data.b64") as f:
        b64_str = f.read().strip()

    for dump in decode_frdump(b64_str):
        print(dump)