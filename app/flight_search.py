"""Google Flights URL builder using protobuf wire-format encoding."""

from base64 import urlsafe_b64encode
from urllib.parse import urlencode
from typing import Optional


def _pb_varint(value: int) -> bytes:
    buf = []
    while value > 0x7F:
        buf.append((value & 0x7F) | 0x80)
        value >>= 7
    buf.append(value & 0x7F)
    return bytes(buf)


def _pb_field_varint(field: int, value: int) -> bytes:
    return _pb_varint((field << 3) | 0) + _pb_varint(value)


def _pb_field_bytes(field: int, data: bytes) -> bytes:
    return _pb_varint((field << 3) | 2) + _pb_varint(len(data)) + data


def _pb_field_string(field: int, value: str) -> bytes:
    return _pb_field_bytes(field, value.encode("utf-8"))


def _pb_airport(field: int, iata_code: str) -> bytes:
    inner = _pb_field_varint(1, 1) + _pb_field_string(2, iata_code)
    return _pb_field_bytes(field, inner)


def _pb_flight_data(
    date: str,
    origin: str,
    destination: str,
    airlines: Optional[list[str]] = None,
) -> bytes:
    data = b""
    data += _pb_field_string(2, date)
    if airlines:
        for code in airlines:
            data += _pb_field_string(6, code)
    data += _pb_airport(13, origin)
    data += _pb_airport(14, destination)
    return data


def google_flights_url(
    origin: str,
    destination: str,
    depart_date: str,
    return_date: str,
    airlines: Optional[list[str]] = None,
) -> str:
    """Build a Google Flights search URL with protobuf-encoded tfs parameter."""
    outbound = _pb_flight_data(depart_date, origin, destination, airlines)
    ret = _pb_flight_data(return_date, destination, origin, airlines)

    info = _pb_field_bytes(3, outbound) + _pb_field_bytes(3, ret)
    tfs = urlsafe_b64encode(info).rstrip(b"=").decode("ascii")

    params = {"tfs": tfs, "hl": "en", "gl": "us", "curr": "USD"}
    return f"https://www.google.com/travel/flights/search?{urlencode(params)}"
