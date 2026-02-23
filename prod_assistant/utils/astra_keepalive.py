"""
AstraDB Keep-Alive Utility

Prevents AstraDB Serverless free-tier databases from hibernating
by pinging the database every 12 hours in a background daemon thread.

Usage:
    from prod_assistant.utils.astra_keepalive import start_keepalive
    start_keepalive()  # call once on app startup
"""

import os
import threading
import time
import requests

_keepalive_started = False
_lock = threading.Lock()

PING_INTERVAL_HOURS = 12


def _ping_astra():
    """Background loop that pings AstraDB to prevent hibernation."""
    endpoint = os.getenv("ASTRA_DB_API_ENDPOINT", "")
    token = os.getenv("ASTRA_DB_APPLICATION_TOKEN", "")
    if not endpoint or not token:
        print("⚠️ AstraDB keep-alive disabled: missing ASTRA_DB_API_ENDPOINT or ASTRA_DB_APPLICATION_TOKEN")
        return
    keyspace = os.getenv("ASTRA_DB_KEYSPACE", "default_keyspace").strip('"')

    while True:
        try:
            resp = requests.post(
                f"{endpoint}/api/json/v1/{keyspace}",
                headers={"Token": token, "Content-Type": "application/json"},
                json={"findCollections": {}},
                timeout=30,
            )
            print(f"🏓 AstraDB keep-alive ping: {resp.status_code}")
        except Exception as e:
            print(f"⚠️ AstraDB keep-alive ping failed: {e}")
        time.sleep(PING_INTERVAL_HOURS * 3600)


def start_keepalive():
    """Start the AstraDB keep-alive thread (safe to call multiple times)."""
    global _keepalive_started
    with _lock:
        if _keepalive_started:
            return
        _keepalive_started = True
    threading.Thread(target=_ping_astra, daemon=True).start()
    print("✅ AstraDB keep-alive thread started")
