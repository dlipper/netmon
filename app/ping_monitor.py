import asyncio
import re
import subprocess
import logging
from typing import Tuple, Optional
from app.config import PING_TARGETS, PING_INTERVAL_SECONDS
from app.database import record_ping, prune_old_data

logger = logging.getLogger("netmon.ping")

def ping_host(host: str, count: int = 2, timeout: int = 2) -> Tuple[bool, Optional[float], float]:
    """
    Pings a host. Returns (is_online, avg_latency_ms, packet_loss_pct).
    """
    try:
        proc = subprocess.run(
            ["ping", "-c", str(count), "-W", str(timeout), "-q", host],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout * count + 2
        )
        
        output = proc.stdout
        # Extract packet loss: "0% packet loss" or "100% packet loss"
        loss_match = re.search(r"(\d+(?:\.\d+)?)%\s+packet loss", output)
        packet_loss = float(loss_match.group(1)) if loss_match else 100.0
        
        # Extract rtt min/avg/max/mdev = 13.048/13.304/13.560/0.256 ms
        rtt_match = re.search(r"rtt min/avg/max/mdev = [\d\.]+/([\d\.]+)/[\d\.]+/[\d\.]+", output)
        avg_latency = float(rtt_match.group(1)) if rtt_match else None
        
        is_online = (packet_loss < 100.0)
        return is_online, avg_latency, packet_loss
    except Exception as e:
        logger.error(f"Error pinging {host}: {e}")
        return False, None, 100.0

async def ping_monitor_loop():
    """
    Continuous background loop that pings targets every PING_INTERVAL_SECONDS.
    """
    logger.info("Starting ping monitor loop...")
    loop_count = 0
    while True:
        try:
            # We ping both targets and compute best status
            target_results = []
            for target in PING_TARGETS:
                online, latency, loss = ping_host(target)
                target_results.append((target, online, latency, loss))
            
            # Store primary result (using 1.1.1.1 or the responding one)
            # If at least one target is reachable, we consider the internet online
            any_online = any(r[1] for r in target_results)
            
            # Pick primary target (or fallback if primary is down)
            primary = target_results[0]
            if not primary[1] and len(target_results) > 1 and target_results[1][1]:
                primary = target_results[1]
                
            record_ping(
                target=primary[0],
                latency_ms=primary[2],
                packet_loss=primary[3],
                is_online=any_online
            )
            
            loop_count += 1
            # Prune once every ~24 hours (2880 loops of 30 seconds)
            if loop_count % 2880 == 0:
                prune_old_data(days=30)
                
        except Exception as e:
            logger.error(f"Error in ping monitor loop: {e}")
            
        await asyncio.sleep(PING_INTERVAL_SECONDS)
