import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from app.config import DB_PATH

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def init_db():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS pings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                target TEXT NOT NULL,
                latency_ms REAL,
                packet_loss REAL NOT NULL,
                is_online INTEGER NOT NULL
            );
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_pings_timestamp ON pings(timestamp);
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS speedtests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                download_mbps REAL NOT NULL,
                upload_mbps REAL NOT NULL,
                ping_ms REAL NOT NULL,
                jitter_ms REAL,
                packet_loss REAL,
                server_name TEXT,
                server_location TEXT,
                server_country TEXT,
                isp TEXT,
                client_ip TEXT,
                result_url TEXT
            );
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_speedtests_timestamp ON speedtests(timestamp);
        """)

# Automatically ensure tables exist on module load
init_db()

def record_ping(target: str, latency_ms: Optional[float], packet_loss: float, is_online: bool) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO pings (target, latency_ms, packet_loss, is_online)
            VALUES (?, ?, ?, ?)
            """,
            (target, latency_ms, packet_loss, 1 if is_online else 0)
        )

def record_speedtest(
    download_mbps: float,
    upload_mbps: float,
    ping_ms: float,
    jitter_ms: Optional[float] = None,
    packet_loss: Optional[float] = None,
    server_name: Optional[str] = None,
    server_location: Optional[str] = None,
    server_country: Optional[str] = None,
    isp: Optional[str] = None,
    client_ip: Optional[str] = None,
    result_url: Optional[str] = None
) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO speedtests (
                download_mbps, upload_mbps, ping_ms, jitter_ms, packet_loss,
                server_name, server_location, server_country, isp, client_ip, result_url
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                download_mbps, upload_mbps, ping_ms, jitter_ms, packet_loss,
                server_name, server_location, server_country, isp, client_ip, result_url
            )
        )
        return cur.lastrowid

def get_latest_ping() -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        cur = conn.execute("SELECT * FROM pings ORDER BY id DESC LIMIT 1")
        row = cur.fetchone()
        return dict(row) if row else None

def get_latest_speedtest() -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        cur = conn.execute("SELECT * FROM speedtests ORDER BY id DESC LIMIT 1")
        row = cur.fetchone()
        return dict(row) if row else None

def get_uptime_stats(hours: int = 24) -> Dict[str, Any]:
    with get_connection() as conn:
        cur = conn.execute(
            """
            SELECT 
                COUNT(*) as total_samples,
                SUM(is_online) as online_samples,
                AVG(latency_ms) as avg_latency
            FROM pings
            WHERE timestamp >= datetime('now', ? || ' hours')
            """,
            (f"-{hours}",)
        )
        row = cur.fetchone()
        total = row["total_samples"] if row and row["total_samples"] else 0
        online = row["online_samples"] if row and row["online_samples"] else 0
        avg_latency = round(row["avg_latency"], 1) if row and row["avg_latency"] is not None else None
        
        uptime_pct = round((online / total) * 100, 2) if total > 0 else 100.0
        return {
            "hours": hours,
            "total_samples": total,
            "online_samples": online,
            "uptime_pct": uptime_pct,
            "avg_latency_ms": avg_latency
        }

def get_ping_history(hours: int = 24, max_points: int = 300) -> List[Dict[str, Any]]:
    """Returns ping data points formatted for time-series display."""
    with get_connection() as conn:
        cur = conn.execute(
            """
            SELECT timestamp, target, latency_ms, packet_loss, is_online
            FROM pings
            WHERE timestamp >= datetime('now', ? || ' hours')
            ORDER BY id ASC
            """,
            (f"-{hours}",)
        )
        rows = [dict(r) for r in cur.fetchall()]
        
        # If too many points, downsample slightly while preserving outages
        if len(rows) <= max_points:
            return rows
            
        step = len(rows) / max_points
        downsampled = []
        for i in range(max_points):
            idx = int(i * step)
            downsampled.append(rows[idx])
        return downsampled

def get_speedtests(limit: int = 50) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cur = conn.execute(
            """
            SELECT * FROM speedtests
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,)
        )
        return [dict(r) for r in cur.fetchall()]

def prune_old_data(days: int = 30):
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM pings WHERE timestamp < datetime('now', ? || ' days')",
            (f"-{days}",)
        )
