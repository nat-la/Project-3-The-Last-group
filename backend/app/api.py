from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel
import sqlite3
from typing import List
from typing import Optional
from datetime import datetime, timezone, timedelta
import random
from fastapi.middleware.cors import CORSMiddleware
import os, json, urllib.parse, urllib.request
from pathlib import Path
from dotenv import load_dotenv

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(ENV_PATH)

# ------------------------------------------------------------
# App setup
# ------------------------------------------------------------

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# SQLite DB file location (stored on disk in project directory)
# DB_PATH = "app.db"
DB_PATH = str(Path(__file__).resolve().parent / "app.db")

# ------------------------------------------------------------
# Database helpers
# ------------------------------------------------------------
def get_conn():
    """
    Create and return a SQLite DB connection.

    row_factory makes rows behave like dicts:
      row["id"] instead of row[0]
    This improves readability across the codebase.
    """
    
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """
    Create required database tables if they do not exist.

    Tables:
    - locations: stores saved locations (name + address)
    - commutes: stores commute events between two locations
    """

    conn = get_conn()
    cur = conn.cursor()

    # Locations table: minimal fields for P0 prototype
    cur.execute("""
        CREATE TABLE IF NOT EXISTS locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            address TEXT NOT NULL,
            lat REAL,
            lng REAL
        )
    """)

    # Commutes table:
    # - origin_location_id and destination_location_id reference locations.id
    # - started_at stored as ISO string for simplicity
    cur.execute("""
    CREATE TABLE IF NOT EXISTS commutes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        origin_location_id INTEGER NOT NULL,
        destination_location_id INTEGER NOT NULL,
        mode TEXT NOT NULL,
        estimated_minutes INTEGER NOT NULL,
        actual_minutes INTEGER NOT NULL,
        started_at TEXT NOT NULL,
        FOREIGN KEY (origin_location_id) REFERENCES locations(id),
        FOREIGN KEY (destination_location_id) REFERENCES locations(id)
    )
""")
    

    # Add api_estimated_minutes to commutes if missing
    commute_cols = [r["name"] for r in cur.execute("PRAGMA table_info(commutes)").fetchall()]
    if "api_estimated_minutes" not in commute_cols:
        cur.execute("ALTER TABLE commutes ADD COLUMN api_estimated_minutes INTEGER")

    # Add lat/lng to locations if missing (older DBs)
    location_cols = [r["name"] for r in cur.execute("PRAGMA table_info(locations)").fetchall()]
    if "lat" not in location_cols:
        cur.execute("ALTER TABLE locations ADD COLUMN lat REAL")
    if "lng" not in location_cols:
        cur.execute("ALTER TABLE locations ADD COLUMN lng REAL")

    conn.commit()
    conn.close()

@app.on_event("startup")
def on_startup():
    """
    FastAPI lifecycle hook.

    Runs once when the server process starts.
    Ensures the database schema exists before handling requests.
    """
    init_db()

# ------------------------------------------------------------
# Pydantic models (define request/response shapes)
# ------------------------------------------------------------

class Echo(BaseModel):
    """Used by /echo endpoint for quick request sanity checks."""
    message: str

class LocationCreate(BaseModel):
    """
    Request model for creating or updating a location.
    Does not include DB-generated id.
    """    
    name: str
    address: str
    lat: Optional[float] = None
    lng: Optional[float] = None

class Location(LocationCreate):
    """
    Response model for locations (includes id).
    Inherits name/address from LocationCreate.
    """
    id: int

class CommuteCreate(BaseModel):
    """
    Request model for creating a commute.

    Notes:
    - started_at is optional; if not provided we use 'now' in UTC.
    - mode defaults to "driving" for this prototype.
    """    
    origin_location_id: int
    destination_location_id: int
    mode: str = "driving"
    estimated_minutes: Optional[int] = None
    actual_minutes: int
    started_at: Optional[datetime] = None
    use_api_estimate: bool = True

class Commute(CommuteCreate):
    """Response model for commutes (includes id)."""
    id: int

# ------------------------------------------------------------
# Basic endpoints
# ------------------------------------------------------------

@app.get("/")
def root():
    return {"message": "Hello world"}

@app.post("/echo")
def echo(data: Echo):
    return {"you_sent": data.message}

@app.get("/health")
def health():
    required = ["GOOGLE_MAPS_API_KEY"]
    missing = [k for k in required if not os.getenv(k)]
    return {
        "ok": len(missing) == 0,
        "missing": missing
    }

# ------------------------------------------------------------
# Location endpoints (CRUD)
# ------------------------------------------------------------

# create location
@app.post("/locations", response_model=Location)
def create_location(location_in: LocationCreate):
    """
    Create a new location in the DB.

    Returns:
    - The newly created location including its autogenerated id.
    """
    conn = get_conn() # set var conn equal to server connection
    cur = conn.cursor() # set var cur equal to cursor for server

    # if lat and lng not provided
    lat = location_in.lat
    lng = location_in.lng
    address = location_in.address
    
    if lat is None or lng is None:
        try:
            lat, lng, address = geocode_address(address)
        except HTTPException:
            lat, lng = None, None
            
    cur.execute("INSERT INTO locations (name, address, lat, lng) VALUES (?, ?, ?, ?)",
                (location_in.name, address, lat, lng),
    )
    conn.commit() # save changes to disk (if forgotten, data not saved)
    new_id = cur.lastrowid # autogenerate id
    conn.close() # close database connection
    return Location(id=new_id, name=location_in.name, address=address, lat=lat, lng=lng)

# get location
@app.get("/locations", response_model=list[Location])
def get_locations():
    """
    Fetch all locations.

    Note:
    - ORDER BY id provides stable ordering for the UI.
    """
    conn = get_conn() # get connection to database
    cur = conn.cursor() # get cursor for database
    rows = cur.execute("SELECT id, name, address, lat, lng FROM locations ORDER BY id").fetchall()
    conn.close() # close connection
    return [Location(id=row["id"], name=row["name"], address=row["address"], lat=row["lat"], lng=row["lng"]) for row in rows]

#get location from id
@app.get("/locations/{location_id}", response_model=Location)
def get_location(location_id: int):
    """
    Fetch a specific location by ID.

    If not found:
    - return HTTP 404
    """
    conn = get_conn()
    cur = conn.cursor()
    row = cur.execute("SELECT id, name, address, lat, lng FROM locations WHERE id = ?",
                      (location_id,),
    ).fetchone()
    conn.close()

    if row is None:
        raise HTTPException(status_code=404, detail="Location not found")
    
    return Location(id=row["id"],
                    name=row["name"], 
                    address=row["address"], 
                    lat=row["lat"], 
                    lng=row["lng"]
    )

# delete locaiton
@app.delete("/locations/{location_id}")
def delete_location(location_id: int):
    """
    Delete a location by ID.

    Behavior:
    - If the id doesn't exist, return 404.
    - If it exists, delete and return a small status payload.

    Note:
    - If commutes reference this location, SQLite FK constraints could matter
      depending on how SQLite is configured (FK enforcement is off by default
      unless PRAGMA foreign_keys=ON is set).
    """
    conn = get_conn()
    cur = conn.cursor()

    ref = cur.execute(
        "SELECT COUNT(*) AS n FROM commutes WHERE origin_location_id=? OR destination_location_id=?",
        (location_id, location_id),
    ).fetchone()

    if ref["n"] > 0:
        conn.close()
        raise HTTPException(status_code=400, detail="Cannot delete: location is used by existing commutes")

    cur.execute("DELETE FROM locations WHERE id = ?", (location_id,))
    conn.commit()
    deleted = cur.rowcount
    conn.close()

    if deleted == 0:
        raise HTTPException(status_code=404, detail="Location not found")
    return {"status": "deleted", "id": location_id}

# update location
@app.put("/locations/{location_id}", response_model=Location)
def update_location(location_id: int, location_in: LocationCreate):
    """
    Update a location's name and address.

    If the location doesn't exist:
    - return 404
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
    "UPDATE locations SET name=?, address=?, lat=?, lng=? WHERE id=?",
        (location_in.name, location_in.address, location_in.lat, location_in.lng, location_id),
    )

    conn.commit()
    changed = cur.rowcount
    conn.close()

    if changed == 0:
        raise HTTPException(status_code=404, detail="Location not found")
    
    return Location(id=location_id, **location_in.model_dump())

# ------------------------------------------------------------
# Commute endpoints
# ------------------------------------------------------------

# create commute
@app.post("/commutes", response_model=Commute)
def create_commute(commute_in: CommuteCreate):
    """
    Create a commute record.

    Validations:
    - Minutes must be positive (no 0 or negative commute durations)
    - origin & destination IDs must exist in the locations table

    started_at:
    - If not provided, defaults to current UTC time.
    """
    @app.post("/commutes", response_model=Commute)
    def create_commute(commute_in: CommuteCreate):
        if commute_in.actual_minutes <= 0:
            raise HTTPException(status_code=400, detail="Actual minutes must be positive")

        started_at = commute_in.started_at or datetime.now(timezone.utc)

        conn = get_conn()
        cur = conn.cursor()

        origin = cur.execute("SELECT id, lat, lng FROM locations WHERE id = ?", (commute_in.origin_location_id,)).fetchone()
        dest = cur.execute("SELECT id, lat, lng FROM locations WHERE id = ?", (commute_in.destination_location_id,)).fetchone()

        if origin is None or dest is None:
            conn.close()
            raise HTTPException(status_code=404, detail="Origin or destination location not found")

        # Decide estimate:
        api_est_minutes = None
        est_minutes = commute_in.estimated_minutes

        if commute_in.use_api_estimate:
            if origin["lat"] is None or origin["lng"] is None or dest["lat"] is None or dest["lng"] is None:
                conn.close()
                raise HTTPException(status_code=400, detail="Origin/destination missing lat/lng for API estimate")

            _, _, duration_s = get_route_info(origin["lat"], origin["lng"], dest["lat"], dest["lng"])
            api_est_minutes = max(1, int(round(duration_s / 60)))
            est_minutes = api_est_minutes

        if est_minutes is None or est_minutes <= 0:
            conn.close()
            raise HTTPException(status_code=400, detail="Estimated minutes must be positive (or enable use_api_estimate)")

        cur.execute("""
            INSERT INTO commutes (
                origin_location_id, destination_location_id, mode,
                estimated_minutes, actual_minutes, started_at, api_estimated_minutes
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            commute_in.origin_location_id,
            commute_in.destination_location_id,
            commute_in.mode,
            est_minutes,
            commute_in.actual_minutes,
            started_at.isoformat(),
            api_est_minutes,
        ))

        conn.commit()
        new_id = cur.lastrowid
        conn.close()

        data = commute_in.model_dump()
        data["started_at"] = started_at
        data["estimated_minutes"] = est_minutes  # ensure it reflects API if used

        return Commute(id=new_id, **data)

# display commutes
@app.get("/commutes", response_model=list[Commute])
def list_commutes():
    """
    List all commutes (most recent first).

    Note:
    - started_at is stored in SQLite as an ISO string.
    - We convert it back into a datetime via datetime.fromisoformat().
    """
    conn = get_conn()
    cur = conn.cursor()
    rows = cur.execute("""
        SELECT id, origin_location_id, destination_location_id, mode,
               estimated_minutes, actual_minutes, started_at
        FROM commutes
        ORDER BY id DESC
    """).fetchall()
    conn.close()

    return [
        Commute(
            id=row["id"],
            origin_location_id=row["origin_location_id"],
            destination_location_id=row["destination_location_id"],
            mode=row["mode"],
            estimated_minutes=row["estimated_minutes"],
            actual_minutes=row["actual_minutes"],
            started_at=datetime.fromisoformat(row["started_at"]),
        )
        for row in rows
    ]

# get specific commute from id
@app.get("/commutes/{commute_id}", response_model=Commute)
def get_commute(commute_id: int):
    """
    Retrieve a single commute by ID.

    If not found:
    - return 404
    """
    conn = get_conn()
    cur = conn.cursor()
    row = cur.execute("""
        SELECT id, origin_location_id, destination_location_id, mode,
               estimated_minutes, actual_minutes, started_at
        FROM commutes
        WHERE id = ?
    """, (commute_id,)).fetchone()
    conn.close()

    if row is None:
        raise HTTPException(status_code=404, detail="Commute not found")
    
    return Commute(
        id=row["id"],
        origin_location_id=row["origin_location_id"],
        destination_location_id=row["destination_location_id"],
        mode=row["mode"],
        estimated_minutes=row["estimated_minutes"],
        actual_minutes=row["actual_minutes"],
        started_at=datetime.fromisoformat(row["started_at"]),
    )

# ------------------------------------------------------------
# Debug/test endpoint: seeding fake commutes
# ------------------------------------------------------------

# generate random commutes (for testing)
@app.post("/debug/seed-commutes")
def seed_commutes(n: int = Query(30, ge=1, le=500)):
    """
    TEMP: Generates fake commute records for analytics testing.

    Query parameter:
    - n: number of commutes to generate (default 30)
      ge=1, le=500 means FastAPI validates the range for you.

    Remove or protect this endpoint before production.
    """
    conn = get_conn()
    cur = conn.cursor()

    loc_rows = cur.execute("SELECT id FROM locations ORDER BY id").fetchall()
    loc_ids = [r["id"] for r in loc_rows]

    if len(loc_ids) < 2:
        conn.close()
        raise HTTPException(status_code=400, detail="Need at least 2 locations to seed commutes")
    
    now = datetime.now(timezone.utc)

    inserted = 0
    for _ in range (n):
        origin, dest = random.sample(loc_ids, 2)

        days_ago = random.randint(0, 27)

        # hour = random.choice([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12,])
        # minute = random.choice([0, 10, 15, 20, 25, 30, 35, 45, 50, 55])

        hour = random.randint(1,12)
        minute = random.randint(0, 59)

        started_at = (now - timedelta(days=days_ago)).replace(hour=hour, minute=minute,
                                                              second=random.randint(0, 59), microsecond=random.randint(0, 999999))
        
        est = random.randint(15, 60)

        weekday = int(started_at.strftime("%w"))
        bias = 0
        if weekday == 4:
            bias = random.randint(5, 15)
        elif weekday == 1:
            bias = random.randint(2, 10)
        else:
            bias = random.randint(-3, 8)

        actual = max(5, est + bias + random.randint(-2, 6))

        cur.execute(
            """
            INSERT INTO commutes (
                origin_location_id, destination_location_id, mode,
                estimated_minutes, actual_minutes, started_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """, (origin, dest, "driving", est, actual, started_at.isoformat()),
        )
        inserted += 1

    conn.commit()
    conn.close()

    return {"status": "ok", "inserted": inserted}

# ------------------------------------------------------------
# Analytics endpoints
# ------------------------------------------------------------

# commute summary
@app.get("/analytics/summary")
def analytics_summary():
    """
    High-level summary across all commutes.

    Returns:
    - total_commutes
    - avg_estimated_minutes
    - avg_actual_minutes
    - avg_delay_minutes (actual - estimated)

    Note:
    - AVG(...) in SQL returns NULL if there are no rows,
      so we explicitly handle total == 0.
    """
    conn = get_conn()
    cur = conn.cursor()

    row = cur.execute("""
        SELECT
            COUNT(*) AS total,
            AVG(estimated_minutes) AS avg_est,
            AVG(actual_minutes) AS avg_act,
            AVG(actual_minutes - estimated_minutes) AS avg_delay
        FROM commutes
    """).fetchone()

    conn.close()

    total = row["total"]
    if total == 0:
        return {
            "total_commutes": 0,
            "avg_estimated_minutes": None,
            "avg_actual_minutes": None,
            "avg_delay_minutes": None,
        }
    
    return {
        "total_commutes": total,
            "avg_estimated_minutes": round(row["avg_est"], 2),
            "avg_actual_minutes": round(row["avg_act"], 2),
            "avg_delay_minutes": round(row["avg_delay"], 2),
    }

#commute summary for weekday
@app.get("/analytics/by-weekday")
def analytics_by_weekday():
    """
    Aggregates commute stats by weekday.

    SQLite strftime('%w', started_at) returns:
    0=Sunday, 1=Monday, ... 6=Saturday

    Returns:
    - count (n)
    - avg_actual
    - avg_estimated
    - avg_delay
    """
    conn = get_conn()
    cur = conn.cursor()

    rows = cur.execute("""
        SELECT
            strftime('%w', datetime(started_at)) AS weekday_num,
            COUNT(*) AS n,
            AVG(actual_minutes) AS avg_actual,
            AVG(estimated_minutes) AS avg_estimated,
            AVG(actual_minutes - estimated_minutes) AS avg_delay
        FROM commutes
        GROUP BY weekday_num
        ORDER BY weekday_num
    """).fetchall()

    conn.close()

    weekday_names = {
        "0": "Sunday",
        "1": "Monday",
        "2": "Tuesday",
        "3": "Wednesday",
        "4": "Thursday",
        "5": "Friday",
        "6": "Saturday"
    }

    return [
        {
            "weekday": weekday_names.get(r["weekday_num"], r["weekday_num"]),
            "count": r["n"],
            "avg_actual_minutes": round(r["avg_actual"], 2),
            "avg_estimated_minutes": round(r["avg_estimated"], 2),
            "avg_delay_minutes": round(r["avg_delay"], 2),
        }
        for r in rows
    ]

# give recommendations
@app.get("/analytics/recommendations")
def analytics_recommendations():
    """
    Generates recommendations by weekday.

    Logic:
    1) Compute overall average actual commute time.
    2) Compute average actual time per weekday.
    3) For weekdays with enough samples (n >= 3),
       flag the weekday if avg_actual is >= 15% slower than overall average.

    Returns:
    - recommendations list (can be empty)
    """
    conn = get_conn()
    cur = conn.cursor()

    overall = cur.execute("""
        SELECT COUNT(*) AS total, AVG(actual_minutes) AS overall_avg
        FROM commutes
    """).fetchone()

    total = overall["total"]
    if total == 0:
        conn.close()
        return {"recommendations": [], "reason": "No commute data yet"}
    
    overall_avg = overall["overall_avg"]

    rows = cur.execute("""
        SELECT
            strftime('%w', datetime(started_at)) AS weekday_num,
            COUNT(*) AS n,
            AVG(actual_minutes) AS avg_actual
        FROM commutes
        GROUP BY weekday_num
    """).fetchall()

    conn.close()

    weekday_names = {
        "0": "Sunday",
        "1": "Monday",
        "2": "Tuesday",
        "3": "Wednesday",
        "4": "Thursday",
        "5": "Friday",
        "6": "Saturday"
    }

    recs = []
    for r in rows:
        if r["n"] < 3:
            continue # uses 3 samples for meaningful recommendations

        avg_actual = r["avg_actual"]
        if avg_actual >= overall_avg * 1.15: # should be 1.15 but its 1.05 for testing
            day = weekday_names.get(r["weekday_num"], r["weekday_num"])
            recs.append({
                "type": "weekday_warning",
                "message": f"Your commutes on {day} are consistently slower.",
                "details": {
                    "day_avg_actual": round(avg_actual, 2),
                    "overall_avg_actual": round(overall_avg, 2),
                    "threshold_percent": 15,
                    "samples": r["n"]
                }
            })
    return {"recommendations": recs}

# analytics for specific route
@app.get("/analytics/by-route")
def analytics_by_route():
    """
    Aggregates commute stats by route (origin -> destination).

    Returns for each route:
    - count
    - avg_estimated
    - avg_actual
    - avg_delay
    """
    conn = get_conn()
    cur = conn.cursor()

    rows = cur.execute("""
        SELECT
            origin_location_id,
            destination_location_id,
            COUNT(*) AS n,
            AVG(estimated_minutes) AS avg_estimated,
            AVG(actual_minutes) AS avg_actual,
            AVG(actual_minutes - estimated_minutes) AS avg_delay
        FROM commutes
        GROUP BY origin_location_id, destination_location_id
        ORDER BY n DESC
    """).fetchall()

    conn.close()

    return [
        {
            "origin_location_id": r["origin_location_id"],
            "destination_location_id": r["destination_location_id"],
            "count": r["n"],
            "avg_estimated_minutes": round(r["avg_estimated"], 2),
            "avg_actual_minutes": round(r["avg_actual"], 2),
            "avg_delay_minutes": round(r["avg_delay"], 2),
        }
        for r in rows
    ]

# recommendations by route
@app.get("/analytics/recommendations-by-route")
def analytics_recommendation_by_route(
    pct_threshold: float = Query(0.15, ge=0.01, le=1.00),
    min_samples: int = Query(5, ge=1, le=200),
    top: int = Query(10, ge=1, le=50)):
    """
    Route-based recommendations.

    Query params:
    - pct_threshold: how much worse actual/estimated must be to flag
        Example: 0.15 = 15% worse
    - min_samples: minimum number of commutes required before we consider a route
    - top: max number of routes returned (sorted worst-first)

    Output:
    - returns the top N routes by "percent_worse_than_estimated"
    - includes is_flagged boolean based on threshold
    - shows worst routes even if none are flagged (for visibility)
    """

    conn = get_conn()
    cur = conn.cursor()

    rows = cur.execute("""
        SELECT
            origin_location_id,
            destination_location_id,
            COUNT(*) AS n,
            AVG(estimated_minutes) AS avg_est,
            AVG(actual_minutes) AS avg_act
        FROM commutes
        GROUP BY origin_location_id, destination_location_id
        HAVING COUNT(*) >= ?
    """, (min_samples,)).fetchall()

    conn.close()

    route_stats = []
    for r in rows:
        avg_est = float(r["avg_est"] or 0.0)
        avg_act = float(r["avg_act"] or 0.0)
        if avg_est <= 0:
            continue

        ratio = avg_act / avg_est
        pct_over = (ratio - 1.0) * 100.0

        route_stats.append({
            "origin_location_id": r["origin_location_id"],
            "destination_location_id": r["destination_location_id"],
            "count": r["n"],
            "avg_estimated_minutes": round(avg_est, 2),
            "avg_actual_minutes": round(avg_act, 2),
            "percent_worse_than_estimated": round(pct_over, 1),
            "threshold_percent": round(pct_threshold * 100, 1),
            "is_flagged": ratio >= (1.0 + pct_threshold),
            "recommendation": (
                "Consider leaving earlier or choosing a different route."
                if ratio >= (1.0 + pct_threshold)
                else "No action needed (below threshold)."
            ),
        })

    # Show the “worst” routes even if none pass the threshold
    route_stats.sort(key=lambda x: x["percent_worse_than_estimated"], reverse=True)
    return route_stats[:top]

# analytics by hour
@app.get("/analytics/by-hour")
def analytics_by_hour():
    """
    Aggregates commute stats by hour-of-day.

    How hour is computed:
    - started_at stored as string
    - datetime(started_at) converts it to SQLite datetime
    - strftime('%H', ...) extracts hour 00-23
    - CAST(... AS INTEGER) ensures numeric sorting
    """
    conn = get_conn()
    cur = conn.cursor()

    rows = cur.execute("""
        SELECT
            CAST(strftime('%H', datetime(started_at)) AS INTEGER) AS hour,
            COUNT(*) AS n,
            AVG(estimated_minutes) AS avg_est,
            AVG(actual_minutes) AS avg_act,
            AVG(actual_minutes - estimated_minutes) AS avg_delay
        FROM commutes
        GROUP BY hour
        ORDER BY hour
    """).fetchall()

    conn.close()

    return [
        {
            "hour": r["hour"],
            "count": r["n"],
            "avg_estimated_minutes": round(r["avg_est"], 2),
            "avg_actual_minutes": round(r["avg_act"], 2),
            "avg_delay_minutes": round(r["avg_delay"], 2),
        }
        for r in rows
    ]

# recommendations based on hour
@app.get("/analytics/recommendations-by-route-hour")
def recommendations_by_route_hour(
    pct_threshold: float = Query(0.15, ge=0.01, le=1.00),
    min_samples: int = Query(5, ge=1, le=200),
    top: int = Query(10, ge=1, le=50),
    origin_id: int | None = Query(None, ge=1),
    destination_id: int | None = Query(None, ge=1),
):
    """
    Route + hour recommendations.

    This endpoint finds "problem routes at specific hours".

    For each (origin, destination, hour):
    - compute avg_est and avg_act
    - compute percent worse than estimated
    - flag if (avg_act / avg_est) >= 1 + pct_threshold
    - return only flagged items, worst-first

    Use case:
    - "This route is fine normally, but at 5pm it becomes consistently bad."
    """

    conn = get_conn()
    cur = conn.cursor()

    where = ""
    params: list = [min_samples]

    if origin_id is not None and destination_id is not None:
        where = "WHERE origin_location_id = ? AND destination_location_id = ?"
        params = [origin_id, destination_id, min_samples]

    rows = cur.execute(f"""
        SELECT
            origin_location_id,
            destination_location_id,
            CAST(strftime('%H', datetime(started_at)) AS INTEGER) AS hour,
            COUNT(*) AS n,
            AVG(estimated_minutes) AS avg_est,
            AVG(actual_minutes) AS avg_act
        FROM commutes
        {where}
        GROUP BY origin_location_id, destination_location_id, hour
        HAVING COUNT(*) >= ?
    """, tuple(params)).fetchall()

    conn.close()

    items = []
    for r in rows:
        avg_est = float(r["avg_est"] or 0.0)
        avg_act = float(r["avg_act"] or 0.0)
        if avg_est <= 0:
            continue

        ratio = avg_act / avg_est
        pct_over = (ratio - 1.0) * 100.0
        is_flagged = ratio >= (1.0 + pct_threshold)

        # Only filter flagged results in global mode
        if origin_id is None or destination_id is None:
            if not is_flagged:
                continue

        hour = int(r["hour"])
        items.append({
            "origin_location_id": r["origin_location_id"],
            "destination_location_id": r["destination_location_id"],
            "hour": hour,
            "count": r["n"],
            "avg_estimated_minutes": round(avg_est, 2),
            "avg_actual_minutes": round(avg_act, 2),
            "percent_worse_than_estimated": round(pct_over, 1),
            "recommendation": (
                f"This route averages {round(pct_over,1)}% longer than estimated. "
                "Consider leaving earlier or choosing a different route."
            ),
        })

    items.sort(key=lambda x: x["percent_worse_than_estimated"], reverse=True)
    return items[:top]

# all route stats
@app.get("/analytics/route-stats")
def route_stats(origin_id: int = Query(..., ge=1), destination_id: int = Query(..., ge=1)):
    conn = get_conn()
    cur = conn.cursor()

    row = cur.execute("""
        SELECT
            COUNT(*) AS n,
            AVG(estimated_minutes) AS avg_est,
            AVG(actual_minutes) AS avg_act
        FROM commutes
        WHERE origin_location_id = ? AND destination_location_id = ?
    """, (origin_id, destination_id)).fetchone()

    conn.close()

    n = int(row["n"] or 0)
    if n == 0:
        return {
            "origin_location_id": origin_id,
            "destination_location_id": destination_id,
            "count": 0,
            "avg_estimated_minutes": None,
            "avg_actual_minutes": None,
            "percent_worse_than_estimated": None,
        }
    
    avg_est = float(row["avg_est"])
    avg_act = float(row["avg_act"])
    pct_over = ((avg_act / avg_est) - 1.0) * 100 if avg_est > 0 else None

    return {
        "origin_location_id": origin_id,
        "destination_location_id": destination_id,
        "count": n,
        "avg_estimated_minutes": round(avg_est, 2),
        "avg_actual_minutes": round(avg_act, 2),
        "percent_worse_than_estimated": round(pct_over, 1) if pct_over is not None else None,
    }

# ------------------------------------------------------------
# Google API integration
# ------------------------------------------------------------

GOOGLE_GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
def geocode_address(address: str) -> tuple[float, float, str]:
    """
    Uses Google Geocoding API to convert an address into (lat, lng, formatted_address).
    Raises HTTPException on failures.
    """
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="Server missing GOOGLE_MAPS_API_KEY")

    params = {
        "address": address,
        "key": api_key,
    }
    url = GOOGLE_GEOCODE_URL + "?" + urllib.parse.urlencode(params)

    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Geocoding request failed: {e}")

    status = payload.get("status")
    if status != "OK":
        # Common statuses: ZERO_RESULTS, OVER_QUERY_LIMIT, REQUEST_DENIED, INVALID_REQUEST
        raise HTTPException(status_code=400, detail=f"Geocoding failed: {status}")

    result = payload["results"][0]
    loc = result["geometry"]["location"]
    lat = float(loc["lat"])
    lng = float(loc["lng"])
    formatted = result.get("formatted_address", address)

    return lat, lng, formatted

GOOGLE_ROUTES_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"
def get_route_info(origin_lat: float, origin_lng: float, dest_lat: float, dest_lng: float):
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="Server missing GOOGLE_MAPS_API_KEY")

    body = {
        "origin": {"location": {"latLng": {"latitude": origin_lat, "longitude": origin_lng}}},
        "destination": {"location": {"latLng": {"latitude": dest_lat, "longitude": dest_lng}}},
        "travelMode": "DRIVE",
        "polylineQuality": "OVERVIEW",
        "polylineEncoding": "ENCODED_POLYLINE",
    }

    req = urllib.request.Request(
        GOOGLE_ROUTES_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": "routes.polyline.encodedPolyline,routes.duration,routes.distanceMeters",
        },
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=15) as resp:
        payload = json.loads(resp.read().decode("utf-8"))

    routes = payload.get("routes", [])
    if not routes:
        raise HTTPException(status_code=400, detail="No route found")

    r0 = routes[0]
    encoded = r0["polyline"]["encodedPolyline"]
    distance_m = int(r0.get("distanceMeters", 0))

    dur_str = r0.get("duration", "0s")
    duration_s = int(dur_str[:-1]) if isinstance(dur_str, str) and dur_str.endswith("s") else 0

    return encoded, distance_m, duration_s

# Endpoint to get route polyline between two locations
@app.get("/routes/info")
def route_info(origin_id: int = Query(..., ge=1), destination_id: int = Query(..., ge=1)):
    conn = get_conn()
    cur = conn.cursor()

    o = cur.execute("SELECT lat, lng FROM locations WHERE id=?", (origin_id,)).fetchone()
    d = cur.execute("SELECT lat, lng FROM locations WHERE id=?", (destination_id,)).fetchone()
    conn.close()

    if o is None or d is None:
        raise HTTPException(status_code=404, detail="Origin or destination location not found")

    if o["lat"] is None or o["lng"] is None or d["lat"] is None or d["lng"] is None:
        raise HTTPException(status_code=400, detail="Origin/destination missing lat/lng")

    encoded, distance_m, duration_s = get_route_info(o["lat"], o["lng"], d["lat"], d["lng"])

    return {
        "origin_id": origin_id,
        "destination_id": destination_id,
        "encoded_polyline": encoded,
        "distance_meters": distance_m,
        "duration_seconds": duration_s,
    }
