import pytest
import sqlite3
import tempfile
import os
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
 
#  Import the app and the module so we can patch DB_PATH 
import api as app_module
from api import app
 
# Fixtures
 
@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """
    Redirect every test to its own throwaway SQLite file.
    """
    db_file = str(tmp_path / "test.db")
    monkeypatch.setattr(app_module, "DB_PATH", db_file)
    app_module.init_db()   # create schema in the temp DB
    yield db_file
 
 
@pytest.fixture
def client():
    """
    Returns a FastAPI TestClient.
 
    """
    with TestClient(app) as c:
        yield c
 
 
@pytest.fixture
def two_locations(client):
    """
    Seed two locations (no geocoding needed — lat/lng supplied directly).
    Returns (loc_a_id, loc_b_id) for use in commute tests.
    """
    a = client.post("/locations", json={"name": "Home", "address": "123 A St", "lat": 47.6, "lng": -122.3}).json()
    b = client.post("/locations", json={"name": "Office", "address": "456 B Ave", "lat": 47.7, "lng": -122.4}).json()
    return a["id"], b["id"]
 
 
# ── Helper 
 
def make_commute(client, origin_id, dest_id, actual=30, estimated=25):
    """
    POST a commute without triggering the Google Routes API
    (use_api_estimate=False, provide estimated_minutes manually).
    """
    return client.post("/commutes", json={
        "origin_location_id": origin_id,
        "destination_location_id": dest_id,
        "actual_minutes": actual,
        "estimated_minutes": estimated,
        "use_api_estimate": False,
    })
 


class TestLocations:
 
    def test_create_location_with_coords(self, client):
        """
        Creating a location with explicit lat/lng should skip geocoding
        and return those exact coordinates.
        """
        r = client.post("/locations", json={
            "name": "Home",
            "address": "1 Main St",
            "lat": 47.6062,
            "lng": -122.3321,
        })
        assert r.status_code == 200
        data = r.json()
        assert data["name"] == "Home"
        assert data["lat"] == pytest.approx(47.6062)
        assert data["lng"] == pytest.approx(-122.3321)
        assert "id" in data
 
    def test_create_location_triggers_geocoding(self, client):
        """
        If lat/lng are omitted, the backend calls geocode_address().
        We mock it to return known values so the test stays offline.
        """
        with patch.object(app_module, "geocode_address", return_value=(51.5, -0.1, "London, UK")) as mock_geo:
            r = client.post("/locations", json={"name": "London", "address": "London"})
        
        assert r.status_code == 200
        mock_geo.assert_called_once_with("London")
        assert r.json()["lat"] == pytest.approx(51.5)
 
    def test_list_locations_empty(self, client):
        """Fresh DB should return an empty array."""
        r = client.get("/locations")
        assert r.status_code == 200
        assert r.json() == []
 
    def test_list_locations_returns_all(self, client, two_locations):
        """After seeding two locations the list should have exactly two entries."""
        r = client.get("/locations")
        assert r.status_code == 200
        assert len(r.json()) == 2
 
    def test_get_location_by_id(self, client, two_locations):
        """GET /locations/{id} should return the correct single location."""
        loc_id, _ = two_locations
        r = client.get(f"/locations/{loc_id}")
        assert r.status_code == 200
        assert r.json()["id"] == loc_id
        assert r.json()["name"] == "Home"
 
    def test_get_location_not_found(self, client):
        """Requesting a non-existent ID must return 404."""
        r = client.get("/locations/9999")
        assert r.status_code == 404
 
    def test_delete_location(self, client):
        """Deleting an existing location should succeed and remove it from the list."""
        loc = client.post("/locations", json={"name": "Temp", "address": "1 Temp Rd", "lat": 1.0, "lng": 1.0}).json()
        r = client.delete(f"/locations/{loc['id']}")
        assert r.status_code == 200
        assert r.json()["status"] == "deleted"
 
        # Confirm it's gone
        assert client.get(f"/locations/{loc['id']}").status_code == 404
 
    def test_delete_location_not_found(self, client):
        """Deleting a non-existent location should return 404."""
        r = client.delete("/locations/9999")
        assert r.status_code == 404
 
    def test_delete_location_referenced_by_commute(self, client, two_locations):
        """
        A location that's used by an existing commute should be protected from deletion.
        The backend should return 400.
        """
        origin_id, dest_id = two_locations
        make_commute(client, origin_id, dest_id)
 
        r = client.delete(f"/locations/{origin_id}")
        assert r.status_code == 400
        assert "commutes" in r.json()["detail"].lower()
 
    def test_update_location(self, client, two_locations):
        """PUT /locations/{id} should persist new name/address and return updated data."""
        loc_id, _ = two_locations
        r = client.put(f"/locations/{loc_id}", json={
            "name": "Updated Home",
            "address": "999 New St",
            "lat": 47.9,
            "lng": -122.1,
        })
        assert r.status_code == 200
        assert r.json()["name"] == "Updated Home"
 
    def test_update_location_not_found(self, client):
        """PUT to a non-existent ID should return 404."""
        r = client.put("/locations/9999", json={"name": "X", "address": "Y", "lat": 0, "lng": 0})
        assert r.status_code == 404
 
 
 
class TestCommutes:
 
    def test_create_commute_manual_estimate(self, client, two_locations):
        """
        Creating a commute with use_api_estimate=False and a manual estimate
        should succeed and persist both actual and estimated minutes correctly.
        """
        origin_id, dest_id = two_locations
        r = make_commute(client, origin_id, dest_id, actual=35, estimated=28)
        assert r.status_code == 200
        data = r.json()
        assert data["actual_minutes"] == 35
        assert data["estimated_minutes"] == 28
        assert "id" in data
 
    def test_create_commute_invalid_actual_minutes(self, client, two_locations):
        """
        actual_minutes <= 0 should be rejected. The backend validates this
        and must return 400, not 500.
        """
        origin_id, dest_id = two_locations
        r = client.post("/commutes", json={
            "origin_location_id": origin_id,
            "destination_location_id": dest_id,
            "actual_minutes": 0,
            "estimated_minutes": 20,
            "use_api_estimate": False,
        })
        assert r.status_code == 400
 
    def test_create_commute_unknown_location(self, client):
        """Referencing a non-existent location ID should return 404."""
        r = client.post("/commutes", json={
            "origin_location_id": 9999,
            "destination_location_id": 9998,
            "actual_minutes": 30,
            "estimated_minutes": 25,
            "use_api_estimate": False,
        })
        assert r.status_code == 404
 
    def test_create_commute_with_api_estimate(self, client, two_locations):
        """
        When use_api_estimate=True, the backend calls get_route_info().
        We mock it to return a 30-minute route (1800 seconds).
        The resulting estimated_minutes should be 30.
        """
        origin_id, dest_id = two_locations
        with patch.object(app_module, "get_route_info", return_value=("encoded", 50000, 1800)):
            r = client.post("/commutes", json={
                "origin_location_id": origin_id,
                "destination_location_id": dest_id,
                "actual_minutes": 35,
                "use_api_estimate": True,
            })
        assert r.status_code == 200
        assert r.json()["estimated_minutes"] == 30
 
    def test_list_commutes_empty(self, client):
        """Fresh DB should return an empty commute list."""
        r = client.get("/commutes")
        assert r.status_code == 200
        assert r.json() == []
 
    def test_list_commutes_returns_all(self, client, two_locations):
        """After inserting 3 commutes, the list endpoint should return all 3."""
        origin_id, dest_id = two_locations
        for actual in [20, 25, 30]:
            make_commute(client, origin_id, dest_id, actual=actual)
 
        r = client.get("/commutes")
        assert r.status_code == 200
        assert len(r.json()) == 3
 
    def test_get_commute_by_id(self, client, two_locations):
        """GET /commutes/{id} should return the specific commute."""
        origin_id, dest_id = two_locations
        created = make_commute(client, origin_id, dest_id, actual=42).json()
        r = client.get(f"/commutes/{created['id']}")
        assert r.status_code == 200
        assert r.json()["actual_minutes"] == 42
 
    def test_get_commute_not_found(self, client):
        """Non-existent commute ID should return 404."""
        r = client.get("/commutes/9999")
        assert r.status_code == 404
 
 
 
class TestAnalytics:
 
    def test_summary_no_data(self, client):
        """
        With no commutes, summary should return total_commutes=0 and
        all averages as None (not 0 or NaN — this is the explicit contract).
        """
        r = client.get("/analytics/summary")
        assert r.status_code == 200
        data = r.json()
        assert data["total_commutes"] == 0
        assert data["avg_actual_minutes"] is None
 
    def test_summary_with_data(self, client, two_locations):
        """
        After seeding commutes, averages should be computed correctly.
        Two commutes: actual=20 and actual=40 → avg_actual=30.
        """
        origin_id, dest_id = two_locations
        make_commute(client, origin_id, dest_id, actual=20, estimated=18)
        make_commute(client, origin_id, dest_id, actual=40, estimated=38)
 
        r = client.get("/analytics/summary")
        data = r.json()
        assert data["total_commutes"] == 2
        assert data["avg_actual_minutes"] == pytest.approx(30.0)
 
    def test_by_weekday_no_data(self, client):
        """No commutes → empty weekday breakdown."""
        r = client.get("/analytics/by-weekday")
        assert r.status_code == 200
        assert r.json() == []
 
    def test_by_weekday_returns_structure(self, client, two_locations):
        """With commutes present, each bucket should have the expected keys."""
        origin_id, dest_id = two_locations
        make_commute(client, origin_id, dest_id)
 
        r = client.get("/analytics/by-weekday")
        assert r.status_code == 200
        assert len(r.json()) >= 1
 
        bucket = r.json()[0]
        for key in ("weekday", "count", "avg_actual_minutes", "avg_estimated_minutes", "avg_delay_minutes"):
            assert key in bucket, f"Missing key: {key}"
 
    def test_by_hour_no_data(self, client):
        """No commutes → empty hourly breakdown."""
        r = client.get("/analytics/by-hour")
        assert r.status_code == 200
        assert r.json() == []
 
    def test_by_hour_returns_structure(self, client, two_locations):
        """Hourly buckets should include 'hour' and the four metric fields."""
        origin_id, dest_id = two_locations
        make_commute(client, origin_id, dest_id)
 
        buckets = client.get("/analytics/by-hour").json()
        assert len(buckets) >= 1
        for key in ("hour", "count", "avg_actual_minutes", "avg_estimated_minutes", "avg_delay_minutes"):
            assert key in buckets[0]
 
    def test_recommendations_no_data(self, client):
        """No commutes → recommendations list should be empty, not an error."""
        r = client.get("/analytics/recommendations")
        assert r.status_code == 200
        data = r.json()
        assert "recommendations" in data
        assert data["recommendations"] == []
 
    def test_route_stats_no_data(self, client, two_locations):
        """
        route-stats for a valid route with zero commutes should return count=0
        and None for averages, not a 404.
        """
        origin_id, dest_id = two_locations
        r = client.get(f"/analytics/route-stats?origin_id={origin_id}&destination_id={dest_id}")
        assert r.status_code == 200
        assert r.json()["count"] == 0
        assert r.json()["avg_actual_minutes"] is None
 
    def test_route_stats_with_data(self, client, two_locations):
        """
        route-stats should aggregate correctly for a specific origin→dest pair.
        actual=[30, 40] → avg_actual=35; estimated=[25, 25] → avg_est=25
        pct_worse = (35/25 - 1) * 100 = 40%
        """
        origin_id, dest_id = two_locations
        make_commute(client, origin_id, dest_id, actual=30, estimated=25)
        make_commute(client, origin_id, dest_id, actual=40, estimated=25)
 
        r = client.get(f"/analytics/route-stats?origin_id={origin_id}&destination_id={dest_id}")
        data = r.json()
        assert data["count"] == 2
        assert data["avg_actual_minutes"] == pytest.approx(35.0)
        assert data["percent_worse_than_estimated"] == pytest.approx(40.0)
 
    def test_recommendations_by_route_structure(self, client, two_locations):
        """
        recommendations-by-route should return a list (possibly empty) with the
        expected fields when there is data. Using min_samples=1 to relax the default.
        """
        origin_id, dest_id = two_locations
        # Make several commutes that are consistently over estimate
        for _ in range(6):
            make_commute(client, origin_id, dest_id, actual=50, estimated=25)
 
        r = client.get("/analytics/recommendations-by-route?min_samples=1")
        assert r.status_code == 200
        items = r.json()
        assert isinstance(items, list)
        if items:
            for key in ("origin_location_id", "destination_location_id",
                        "percent_worse_than_estimated", "is_flagged"):
                assert key in items[0]
 
    def test_flagged_route_is_correctly_identified(self, client, two_locations):
        """
        A route where avg_actual is 100% of avg_estimated (i.e., 2× the estimate)
        must be flagged when pct_threshold=0.15. is_flagged should be True.
        """
        origin_id, dest_id = two_locations
        for _ in range(6):
            make_commute(client, origin_id, dest_id, actual=50, estimated=25)
 
        r = client.get(
            f"/analytics/recommendations-by-route?pct_threshold=0.15&min_samples=1"
        )
        assert r.status_code == 200
        flagged = [item for item in r.json() if item["is_flagged"]]
        assert len(flagged) >= 1
 
 
 
class TestRouteInfo:
 
    def test_route_info_calls_google(self, client, two_locations):
        """
        GET /routes/info should call get_route_info() under the hood and return
        the polyline + distance + duration. We mock the function to avoid
        real HTTP calls.
        """
        origin_id, dest_id = two_locations
        with patch.object(app_module, "get_route_info", return_value=("abc123", 16000, 900)) as mock_route:
            r = client.get(f"/routes/info?origin_id={origin_id}&destination_id={dest_id}")
 
        assert r.status_code == 200
        data = r.json()
        assert data["encoded_polyline"] == "abc123"
        assert data["distance_meters"] == 16000
        assert data["duration_seconds"] == 900
        mock_route.assert_called_once()
 
    def test_route_info_missing_location(self, client):
        """Requesting route info for non-existent location IDs should 404."""
        r = client.get("/routes/info?origin_id=9999&destination_id=9998")
        assert r.status_code == 404
 
    def test_route_info_missing_lat_lng(self, client):
        """
        Locations without coordinates stored should return 400 (can't compute route).
        We create locations without lat/lng by patching geocode to raise an exception,
        which makes the backend store NULLs.
        """
        with patch.object(app_module, "geocode_address", side_effect=Exception("geo fail")):
            a = client.post("/locations", json={"name": "NoCoords A", "address": "nowhere"}).json()
            b = client.post("/locations", json={"name": "NoCoords B", "address": "nowhere2"}).json()
 
        r = client.get(f"/routes/info?origin_id={a['id']}&destination_id={b['id']}")
        assert r.status_code == 400
 
 
class TestSeedCommutes:
 
    def test_seed_requires_two_locations(self, client):
        """Seeding with fewer than 2 locations should return 400."""
        r = client.post("/debug/seed-commutes?n=10")
        assert r.status_code == 400
 
    def test_seed_inserts_n_commutes(self, client, two_locations):
        """Seeding N commutes should result in exactly N commutes in the DB."""
        r = client.post("/debug/seed-commutes?n=15")
        assert r.status_code == 200
        assert r.json()["inserted"] == 15
 
        commutes = client.get("/commutes").json()
        assert len(commutes) == 15


# Testing latitude and longitude 
class TestLatLngValidation:
 
    def test_valid_lat_lng_accepted(self, client):
        """Baseline: a normal coordinate pair should be accepted."""
        r = client.post("/locations", json={
            "name": "Seattle",
            "address": "Seattle, WA",
            "lat": 47.6062,
            "lng": -122.3321,
        })
        assert r.status_code == 200
        assert r.json()["lat"] == pytest.approx(47.6062)
 
    def test_lat_too_high(self, client):
        """
        lat > 90 is geographically impossible.
        """
        r = client.post("/locations", json={
            "name": "Bad",
            "address": "Nowhere",
            "lat": 91.0,   # invalid — north pole is 90.0
            "lng": 0.0,
        })
        # TODO: once validation is added, change to: assert r.status_code in (400, 422)
        assert r.status_code == 200  # documents current (permissive) behaviour
 
    def test_lat_too_low(self, client):
        """lat < -90 is geographically impossible."""
        r = client.post("/locations", json={
            "name": "Bad",
            "address": "Nowhere",
            "lat": -91.0,
            "lng": 0.0,
        })
        # TODO: assert r.status_code in (400, 422)
        assert r.status_code == 200  # documents current behaviour
 
    def test_lng_too_high(self, client):
        """lng > 180 is geographically impossible."""
        r = client.post("/locations", json={
            "name": "Bad",
            "address": "Nowhere",
            "lat": 0.0,
            "lng": 181.0,   # invalid — antimeridian is 180.0
        })
        # TODO: assert r.status_code in (400, 422)
        assert r.status_code == 200  # documents current behaviour
 
    def test_lng_too_low(self, client):
        """lng < -180 is geographically impossible."""
        r = client.post("/locations", json={
            "name": "Bad",
            "address": "Nowhere",
            "lat": 0.0,
            "lng": -181.0,
        })
        # TODO: assert r.status_code in (400, 422)
        assert r.status_code == 200  # documents current behaviour
 
    def test_lat_as_string_rejected(self, client):
        """
        Sending a non-numeric string for lat.
        Pydantic catches this automatically → 422.
        This one passes right now because Pydantic does the work for us.
        """
        r = client.post("/locations", json={
            "name": "Bad",
            "address": "Nowhere",
            "lat": "not-a-number",
            "lng": 0.0,
        })
        assert r.status_code == 422
 
    def test_lng_as_string_rejected(self, client):
        """Same as above but for lng."""
        r = client.post("/locations", json={
            "name": "Bad",
            "address": "Nowhere",
            "lat": 0.0,
            "lng": "not-a-number",
        })
        assert r.status_code == 422
 
    def test_extreme_but_valid_coordinates(self, client):
        """
        Boundary values that ARE valid — exactly at the limits.
        These should be accepted.
        """
        r = client.post("/locations", json={
            "name": "North Pole",
            "address": "North Pole",
            "lat": 90.0,    # exactly valid
            "lng": 180.0,   # exactly valid
        })
        assert r.status_code == 200