from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel
import sqlite3
from typing import List
from typing import Optional
from datetime import datetime, timezone, timedelta
import random
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = "app.db"

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    # locations table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            address TEXT NOT NULL
        )
    """)

    # commutes table
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
    conn.commit()
    conn.close()

@app.on_event("startup")
def on_startup():
    init_db()

class Echo(BaseModel):
    message: str

class LocationCreate(BaseModel):
    name: str
    address: str

class Location(LocationCreate):
    id: int

class CommuteCreate(BaseModel):
    origin_location_id: int
    destination_location_id: int
    mode: str = "driving"
    estimated_minutes: int
    actual_minutes: int
    started_at: Optional[datetime] = None

class Commute(CommuteCreate):
    id: int

@app.get("/")
def root():
    return {"message": "Hello world"}

@app.post("/echo")
def echo(data: Echo):
    return {"you_sent": data.message}

# create location
@app.post("/locations", response_model=Location)
def create_location(location_in: LocationCreate):
    conn = get_conn() # set var conn equal to server connection
    cur = conn.cursor() # set var cur equal to cursor for server
    cur.execute("INSERT INTO locations (name, address) VALUES (?, ?)",
                (location_in.name, location_in.address),
    )
    conn.commit() # save changes to disk (if forgotten, data not saved)
    new_id = cur.lastrowid # autogenerate id
    conn.close() # close database connection
    return Location(id=new_id, **location_in.model_dump())

# get location
@app.get("/locations", response_model=list[Location])
def get_locations():
    conn = get_conn() # get connection to database
    cur = conn.cursor() # get cursor for database
    rows = cur.execute("SELECT id, name, address FROM locations ORDER BY id").fetchall()
    conn.close() # close connection
    return [Location(id=row["id"], name=row["name"], address=row["address"]) for row in rows]

#get location from id
@app.get("/locations/{location_id}", response_model=Location)
def get_location(location_id: int):
    conn = get_conn()
    cur = conn.cursor()
    row = cur.execute("SELECT id, name, address FROM locations WHERE id = ?",
                      (location_id,),
    ).fetchone()
    conn.close()

    if row is None:
        raise HTTPException(status_code=404, detail="Location not found")
    
    return Location(id=row["id"], name=row["name"], address=row["address"])

# delete locaiton
@app.delete("/locations/{location_id}")
def delete_location(location_id: int):
    conn = get_conn()
    cur = conn.cursor()
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
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE locations SET name = ?, address = ? WHERE id = ?",
        (location_in.name, location_in.address, location_id),)
    conn.commit()
    changed = cur.rowcount
    conn.close()

    if changed == 0:
        raise HTTPException(status_code=404, detail="Location not found")
    
    return Location(id=location_id, **location_in.model_dump())

# create commute
@app.post("/commutes", response_model=Commute)
def creat_commute(commute_in: CommuteCreate):
    if commute_in.estimated_minutes <= 0 or commute_in.actual_minutes <= 0:
        raise HTTPException(status_code=400, detail="Minutes must be positive")
    
    started_at = commute_in.started_at or datetime.now(timezone.utc)

    conn = get_conn()
    cur = conn.cursor()

    origin = cur.execute("SELECT id FROM locations WHERE id = ?", (commute_in.origin_location_id,)).fetchone()
    dest = cur.execute("SELECT id FROM locations WHERE id = ?", (commute_in.destination_location_id,)).fetchone()

    if origin is None or dest is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Origin or destination location not found")
    
    cur.execute("""
        INSERT INTO commutes (
            origin_location_id, destination_location_id, mode,
            estimated_minutes, actual_minutes, started_at
        ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            commute_in.origin_location_id,
            commute_in.destination_location_id,
            commute_in.mode,
            commute_in.estimated_minutes,
            commute_in.actual_minutes,
            started_at.isoformat(),
        ),
    )

    conn.commit()
    new_id = cur.lastrowid
    conn.close()

    data = commute_in.model_dump()
    data["started_at"] = started_at

    return Commute(id=new_id, **data)

# display commutes
@app.get("/commutes", response_model=list[Commute])
def list_commutes():
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

# generate random commutes (for testing)
@app.post("/debug/seed-commutes")
def seed_commutes(n: int = Query(30, ge=1, le=500)):
    """
    TEMP: Generates fake commutes for analytics testing.
    Remove before final submission.
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

        hour = random.choice([6, 7, 8, 16, 17, 18])
        minute = random.choice([0, 10, 15, 20, 25, 30, 35, 45, 50, 55])
        started_at = (now - timedelta(days=days_ago)).replace(hour=hour, minute=minute,
                                                              second=0, microsecond=0)
        
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

# commute summary
@app.get("/analytics/summary")
def analytics_summary():
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
    conn = get_conn()
    cur = conn.cursor()

    rows = cur.execute("""
        SELECT
            strftime('%w', started_at) AS weekday_num,
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
            strftime('%w', started_at) AS weekday_num,
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

    # conn = get_conn()
    # cur = conn.cursor()

    # rows = cur.execute("""
    #     SELECT
    #         origin_location_id,
    #         destination_location_id,
    #         COUNT(*) AS n,
    #         AVG(estimated_minutes) AS avg_est,
    #         AVG(actual_minutes) AS avg_act
    #     FROM commutes
    #     GROUP BY origin_location_id, destination_location_id
    #     HAVING n >= ?
    #     ORDER BY n DESC
    # """, (min_samples,)).fetchall()

    # conn.close()

    # recs = []
    # for r in rows:
    #     avg_est = float(r["avg_est"] or 0.0)
    #     avg_act = float(r["avg_est"] or 0.0)

    #     if avg_est <= 0:
    #         continue

    #     ratio = avg_act / avg_est
    #     if ratio >= (1.0 + pct_threshold):
    #         pct_over = (ratio - 1.0) * 100.0
    #         recs.append({
    #             "origin_location_id": r["origin_location_id"],
    #             "destination_location_id": r["destination_location_id"],
    #             "count": r["n"],
    #             "avg_estimated_minutes": round(avg_est, 2),
    #             "avg_actual_minutes": round(avg_act, 2),
    #             "percent_worse_than_estimated": round(pct_over, 1),
    #             "recommendation": (
    #                 f"This route averages {round(pct_over,1)}% longer than estimated. "
    #                 "Consider leaving earlier or choosing a different route."
    #             ),
    #         })

    # recs.sort(key=lambda x: x["percent_worse_than_estimated"], reverse=True)

    # return recs[:top]

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
    top: int = Query(10, ge=1, le=50)):

    conn = get_conn()
    cur = conn.cursor()

    rows = cur.execute("""
        SELECT
            origin_location_id,
            destination_location_id,
            CAST(strftime('%H', datetime(started_at)) AS INTEGER) AS hour,
            COUNT(*) AS n,
            AVG(estimated_minutes) AS avg_est,
            AVG(actual_minutes) AS avg_act
        FROM commutes
        GROUP BY origin_location_id, destination_location_id, hour
        HAVING COUNT(*) >= ?
    """, (min_samples, )).fetchall()

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

        if not is_flagged: # only return flagged items 
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