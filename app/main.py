import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, BackgroundTasks, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from app.database import (
    init_db,
    get_latest_ping,
    get_latest_speedtest,
    get_uptime_stats,
    get_ping_history,
    get_speedtests
)
from app.ping_monitor import ping_monitor_loop
from app.speedtest_runner import run_speedtest, is_speedtest_running

STATIC_DIR = Path(__file__).parent / "static"

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize DB and start background ping monitor task
    init_db()
    ping_task = asyncio.create_task(ping_monitor_loop())
    yield
    # Shutdown: Cancel background task
    ping_task.cancel()
    try:
        await ping_task
    except asyncio.CancelledError:
        pass

app = FastAPI(title="NetMon", lifespan=lifespan)

# Mount static assets
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.api_route("/", methods=["GET", "HEAD"])
async def serve_index():
    return FileResponse(str(STATIC_DIR / "index.html"))

@app.get("/api/status")
async def api_status():
    latest_ping = get_latest_ping()
    latest_speed = get_latest_speedtest()
    stats_24h = get_uptime_stats(hours=24)
    stats_7d = get_uptime_stats(hours=168)
    
    is_online = latest_ping["is_online"] == 1 if latest_ping else False
    
    return {
        "is_online": is_online,
        "latest_ping": latest_ping,
        "stats_24h": stats_24h,
        "stats_7d": stats_7d,
        "speedtest_running": is_speedtest_running(),
        "latest_speedtest": latest_speed
    }

@app.get("/api/ping-history")
async def api_ping_history(hours: int = Query(default=24, ge=1, le=720)):
    # Cap max points to avoid sending huge JSON (e.g. 500 points across the window)
    max_pts = 500 if hours > 6 else 300
    history = get_ping_history(hours=hours, max_points=max_pts)
    return {
        "hours": hours,
        "points": history
    }

@app.get("/api/speedtests")
async def api_speedtests(limit: int = Query(default=50, ge=1, le=200)):
    return {
        "speedtests": get_speedtests(limit=limit)
    }

@app.post("/api/speedtest/run")
async def api_run_speedtest(background_tasks: BackgroundTasks):
    if is_speedtest_running():
        return JSONResponse(
            status_code=409,
            content={"message": "Speedtest is already running."}
        )
    
    # Run speedtest in background thread
    background_tasks.add_task(run_speedtest, source="web")
    return {"message": "Speedtest started", "status": "running"}

@app.get("/api/speedtest/status")
async def api_speedtest_status():
    return {
        "running": is_speedtest_running(),
        "latest": get_latest_speedtest()
    }
