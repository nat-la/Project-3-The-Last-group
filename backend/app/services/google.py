"""
google_maps.py (or similar)

Purpose:
- Thin wrapper around Google Maps APIs used by the backend:
  - Geocoding API: address -> (lat, lng, normalized/pretty address)
  - Distance Matrix API: (origin, dest) -> distance + duration estimates

Design notes:
- Raises ExternalAPIError for any non-OK API-level responses (even if HTTP is 200).
- Uses requests.get(..., timeout=15) to avoid hanging worker threads indefinitely.
"""

import os
import requests


class ExternalAPIError(Exception):
    """Raised when a required API key is missing or an external API returns an error."""
    pass


def _key() -> str:
    """
    Fetch Google Maps API key from env.

    Keeping key lookup in a helper ensures consistent error behavior and keeps the
    calling functions minimal.
    """
    k = os.getenv("GOOGLE_MAPS_API_KEY")
    if not k:
        raise ExternalAPIError("Missing GOOGLE_MAPS_API_KEY")
    return k


def geocode_address(address: str):
    """
    Convert a free-form address string into coordinates via Google Geocoding API.

    Returns:
      (lat: float, lng: float, formatted_address: str)

    Raises:
      - requests.HTTPError if the HTTP request fails (4xx/5xx)
      - ExternalAPIError if Google returns a non-OK status (e.g., ZERO_RESULTS, OVER_QUERY_LIMIT)
    """
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": address, "key": _key()}

    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()  # HTTP-level failure (network, auth, quota errors surfaced as 4xx/5xx)

    data = r.json()
    status = data.get("status")

    # Google returns 200 even for many errors, so we check API-level status explicitly.
    if status != "OK":
        raise ExternalAPIError(f"Geocoding failed: {status}")

    # Use first result (best match). If you care about ambiguity, you might inspect results length/types.
    loc = data["results"][0]["geometry"]["location"]
    formatted = data["results"][0].get("formatted_address", address)

    return loc["lat"], loc["lng"], formatted


def distance_matrix(origin_lat, origin_lng, dest_lat, dest_lng, mode="driving"):
    """
    Fetch distance + travel time between two coordinate points via Google Distance Matrix API.

    Args:
      origin_lat/origin_lng: origin coordinates
      dest_lat/dest_lng: destination coordinates
      mode: travel mode (driving|walking|bicycling|transit)

    Returns dict:
      {
        "distance_m": int,       # meters
        "distance_text": str,    # human-readable distance (e.g., "12.3 mi")
        "duration_s": int,       # seconds
        "duration_text": str,    # human-readable duration (e.g., "25 mins")
      }

    Raises:
      - requests.HTTPError for HTTP-level failures
      - ExternalAPIError for API-level failures
    """
    url = "https://maps.googleapis.com/maps/api/distancematrix/json"
    params = {
        "origins": f"{origin_lat},{origin_lng}",
        "destinations": f"{dest_lat},{dest_lng}",
        "mode": mode,
        "key": _key(),
    }

    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()

    data = r.json()
    status = data.get("status")

    # Top-level API request status (covers quota/auth/invalid request, etc.)
    if status != "OK":
        raise ExternalAPIError(f"Distance Matrix failed: {status}")

    # Per-route element status (covers NO_ROUTE, NOT_FOUND, etc.)
    row = data["rows"][0]["elements"][0]
    if row.get("status") != "OK":
        raise ExternalAPIError(f"Route element failed: {row.get('status')}")

    return {
        "distance_m": row["distance"]["value"],
        "distance_text": row["distance"]["text"],
        "duration_s": row["duration"]["value"],
        "duration_text": row["duration"]["text"],
    }