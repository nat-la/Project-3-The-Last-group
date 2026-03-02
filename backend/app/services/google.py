import os
import requests

class ExternalAPIError(Exception):
    pass

def _key():
    k = os.getenv("GOOGLE_MAPS_API_KEY")
    if not k:
        raise ExternalAPIError("Missing GOOGLE_MAPS_API_KEY")
    return k

def geocode_address(address: str):
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": address, "key": _key()}
    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    data = r.json()

    status = data.get("status")
    if status != "OK":
        raise ExternalAPIError(f"Geocoding failed: {status}")

    loc = data["results"][0]["geometry"]["location"]
    formatted = data["results"][0].get("formatted_address", address)
    return loc["lat"], loc["lng"], formatted

def distance_matrix(origin_lat, origin_lng, dest_lat, dest_lng, mode="driving"):
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
    if status != "OK":
        raise ExternalAPIError(f"Distance Matrix failed: {status}")

    row = data["rows"][0]["elements"][0]
    if row.get("status") != "OK":
        raise ExternalAPIError(f"Route element failed: {row.get('status')}")

    return {
        "distance_m": row["distance"]["value"],
        "distance_text": row["distance"]["text"],
        "duration_s": row["duration"]["value"],
        "duration_text": row["duration"]["text"],
    }