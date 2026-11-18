# Built by Mohie El-Dean

import configparser
import os
import platform
import subprocess
import sys
import time
from datetime import datetime

IS_WINDOWS = platform.system().lower() == "windows"

DEFAULT_CONFIG = """[targets]
; wireless controller / access point
local_ap_ip = 10.18.2.175
; public host to test internet (IP or DNS name)
public_host = ad.ponet

[settings]
; seconds between checks
ping_interval = 5
; ping timeout in milliseconds
ping_timeout_ms = 1000

[logs]
; only state changes (lost / restored)
event_log = network_interruptions.txt
; every single check result
full_log = network_full_log.txt
"""


def app_dir():
    """Folder of the .exe when frozen, else folder of the script."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def load_config():
    path = os.path.join(app_dir(), "config.ini")
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            f.write(DEFAULT_CONFIG)
        print(f"config.ini not found - created a default one at {path}")
        print("Edit it and restart if the values are wrong.\n")
    cfg = configparser.ConfigParser(inline_comment_prefixes=(";",))
    cfg.read(path, encoding="utf-8")
    return {
        "ap": cfg.get("targets", "local_ap_ip"),
        "host": cfg.get("targets", "public_host"),
        "interval": cfg.getfloat("settings", "ping_interval", fallback=5),
        "timeout_ms": cfg.getint("settings", "ping_timeout_ms", fallback=1000),
        "event_log": os.path.join(app_dir(), cfg.get("logs", "event_log", fallback="network_interruptions.txt")),
        "full_log": os.path.join(app_dir(), cfg.get("logs", "full_log", fallback="network_full_log.txt")),
    }


CFG = load_config()


def ping(host):
    """True if host really replies to a ping."""
    if IS_WINDOWS:
        cmd = ["ping", "-n", "1", "-w", str(CFG["timeout_ms"]), host]
    else:
        cmd = ["ping", "-c", "1", "-W", str(max(1, CFG["timeout_ms"] // 1000)), host]
    try:
        kwargs = {}
        if IS_WINDOWS:
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        r = subprocess.run(cmd, capture_output=True,
                           timeout=CFG["timeout_ms"] / 1000 + 2, **kwargs)
        # Windows returns 0 even for "Destination host unreachable",
        # so also require a real reply (TTL=) in the output.
        return r.returncode == 0 and b"ttl=" in (r.stdout or b"").lower()
    except subprocess.TimeoutExpired:
        return False


def write(path, line):
    with open(path, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def ts():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log_event(message):
    """State changes: console + event log + full log."""
    line = f"[{ts()}] {message}"
    print(line, flush=True)
    write(CFG["event_log"], line)
    write(CFG["full_log"], line)


def main():
    ap, host = CFG["ap"], CFG["host"]
    print("--- Monitoring Started ---")
    print("Built by Mohie El-Dean")
    print(f"Checking Local AP ({ap}) and Public Internet ({host})...")
    print(f"Event log: {CFG['event_log']}")
    print(f"Full log:  {CFG['full_log']}\n")
    open(CFG["event_log"], "a", encoding="utf-8").close()
    write(CFG["full_log"], f"[{ts()}] === Monitoring started (AP={ap}, Internet={host}) ===")

    was_ap_down = False
    was_internet_down = False

    try:
        while True:
            ap_alive = ping(ap)
            internet_alive = ping(host)

            if not ap_alive:
                if not was_ap_down:
                    log_event(f"CRITICAL: Lost connection to the Access Point ({ap})!")
                    was_ap_down = True
            elif was_ap_down:
                log_event(f"SUCCESS: Connection to the Access Point ({ap}) restored.")
                was_ap_down = False

            if ap_alive and not internet_alive:
                if not was_internet_down:
                    log_event(f"WARNING: Connected to AP, but INTERNET IS DOWN (Failed to ping {host}).")
                    was_internet_down = True
            elif was_internet_down and internet_alive:
                log_event("SUCCESS: Internet connectivity restored.")
                was_internet_down = False

            status = (f"AP: {'ONLINE' if ap_alive else 'OFFLINE'} | "
                      f"Internet: {'ONLINE' if internet_alive else 'OFFLINE'}")
            line = f"[{ts()}] {status}"
            print(line, flush=True)
            write(CFG["full_log"], line)

            time.sleep(CFG["interval"])
    except KeyboardInterrupt:
        msg = f"[{ts()}] Monitoring stopped by user."
        print("\n" + msg)
        write(CFG["full_log"], msg)


if __name__ == "__main__":
    main()
