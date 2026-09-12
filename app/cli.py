#!/usr/bin/env python3
import sys
import time
import threading
from app.speedtest_runner import run_speedtest, is_speedtest_running

def animated_spinner(stop_event):
    chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    idx = 0
    start_time = time.time()
    while not stop_event.is_set():
        elapsed = int(time.time() - start_time)
        sys.stdout.write(f"\r\033[1;36m{chars[idx % len(chars)]}\033[0m Testing connection speed... ({elapsed}s)")
        sys.stdout.flush()
        idx += 1
        time.sleep(0.1)
    sys.stdout.write("\r\033[K")
    sys.stdout.flush()

def main():
    print("==================================================")
    print("      NetMon Speedtest & Internet Monitor         ")
    print("==================================================")
    
    if is_speedtest_running():
        print("\033[1;31mError: Another speedtest is currently running.\033[0m")
        sys.exit(1)
        
    stop_event = threading.Event()
    spinner_thread = threading.Thread(target=animated_spinner, args=(stop_event,))
    spinner_thread.daemon = True
    spinner_thread.start()
    
    try:
        result = run_speedtest(source="cli")
    finally:
        stop_event.set()
        spinner_thread.join()
        
    if "error" in result:
        print(f"\n\033[1;31mSpeedtest failed: {result['error']}\033[0m\n")
        sys.exit(1)
        
    print("\n\033[1;32m✓ Speedtest Complete!\033[0m\n")
    print(f"  • Server   : {result.get('server')}")
    print(f"  • ISP      : {result.get('isp')} (IP: {result.get('client_ip')})")
    print(f"  • Ping     : \033[1;33m{result.get('ping_ms')} ms\033[0m (Jitter: {result.get('jitter_ms')} ms)")
    if result.get('packet_loss') is not None:
        print(f"  • Loss     : {result.get('packet_loss')}%")
    print(f"  • Download : \033[1;32m{result.get('download_mbps')} Mbps\033[0m")
    print(f"  • Upload   : \033[1;34m{result.get('upload_mbps')} Mbps\033[0m")
    if result.get('result_url'):
        print(f"  • Result   : {result.get('result_url')}")
    print("\n\033[0;37m✓ Saved to NetMon database and synced to web dashboard.\033[0m\n")

if __name__ == "__main__":
    main()
