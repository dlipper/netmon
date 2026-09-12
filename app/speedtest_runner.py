import json
import subprocess
import threading
from typing import Dict, Any, Optional
from app.config import SPEEDTEST_BIN
from app.database import record_speedtest

_speedtest_lock = threading.Lock()
_is_running = False

def is_speedtest_running() -> bool:
    global _is_running
    return _is_running

def run_speedtest(source: str = "web") -> Dict[str, Any]:
    """
    Executes Ookla speedtest binary and records results to the database.
    Returns parsed metrics dictionary.
    """
    global _is_running
    if not _speedtest_lock.acquire(blocking=False):
        return {"error": "A speedtest is already in progress. Please wait."}

    _is_running = True
    try:
        cmd = [
            str(SPEEDTEST_BIN),
            "--format=json",
            "--accept-license",
            "--accept-gdpr"
        ]
        
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=120
        )
        
        if proc.returncode != 0:
            err_msg = proc.stderr.strip() or f"Speedtest failed with exit code {proc.returncode}"
            return {"error": err_msg}
            
        data = json.loads(proc.stdout)
        
        # Bandwidth in Ookla JSON is in bytes per second. Convert to Megabits per second (Mbps).
        # 1 byte = 8 bits. 1 Mbps = 1,000,000 bits/sec.
        download_bytes = data.get("download", {}).get("bandwidth", 0)
        upload_bytes = data.get("upload", {}).get("bandwidth", 0)
        
        download_mbps = round((download_bytes * 8) / 1_000_000, 2)
        upload_mbps = round((upload_bytes * 8) / 1_000_000, 2)
        
        ping_latency = round(data.get("ping", {}).get("latency", 0), 2)
        ping_jitter = round(data.get("ping", {}).get("jitter", 0), 2)
        packet_loss = data.get("packetLoss", None)
        if packet_loss is not None:
            packet_loss = round(float(packet_loss), 2)
            
        server_info = data.get("server", {})
        server_name = server_info.get("name", "Unknown")
        server_location = server_info.get("location", "Unknown")
        server_country = server_info.get("country", "")
        
        isp = data.get("isp", "Unknown")
        client_ip = data.get("interface", {}).get("externalIp", "")
        result_url = data.get("result", {}).get("url", "")
        
        row_id = record_speedtest(
            download_mbps=download_mbps,
            upload_mbps=upload_mbps,
            ping_ms=ping_latency,
            jitter_ms=ping_jitter,
            packet_loss=packet_loss,
            server_name=server_name,
            server_location=server_location,
            server_country=server_country,
            isp=isp,
            client_ip=client_ip,
            result_url=result_url
        )
        
        return {
            "id": row_id,
            "timestamp": data.get("timestamp"),
            "download_mbps": download_mbps,
            "upload_mbps": upload_mbps,
            "ping_ms": ping_latency,
            "jitter_ms": ping_jitter,
            "packet_loss": packet_loss,
            "server": f"{server_name} ({server_location})",
            "isp": isp,
            "client_ip": client_ip,
            "result_url": result_url
        }
    except subprocess.TimeoutExpired:
        return {"error": "Speedtest timed out after 120 seconds."}
    except json.JSONDecodeError:
        return {"error": "Failed to parse speedtest output JSON."}
    except Exception as e:
        return {"error": str(e)}
    finally:
        _is_running = False
        _speedtest_lock.release()
