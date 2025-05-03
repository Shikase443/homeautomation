# scanner.py
import os
import sys
import time
import json
import asyncio
import requests
from bleak import BleakScanner

# --- Config ------------------------------------------------------------------

# Elasticsearch host (no index path)
ES_HOST     = os.getenv("ES_HOST")
ES_USER     = os.getenv("ES_USER")
ES_PASSWORD = os.getenv("ES_PASSWORD")

RATE_LIMIT_SECONDS = float(os.getenv("RATESEC"))

if not ES_HOST:
    print("ES_HOST is not set", file=sys.stderr)
    sys.exit(1)

DEVICE_CONFIG = {
    "f160fac08dbe": {
        "fields": ["outside_illuminance"],
        "extractor": lambda md: (extract_illuminance(md),)
    },
    "cbb908ebec07": {
        "fields": ["outside_humidity", "outside_temperature"],
        "extractor": lambda md: extract_env(md)
    },
    "e50010000ef1": {
        "fields": ["humidity", "temperature", "illuminance"],
        "extractor": lambda md: extract_enocean(md)
    },
}

last_emit_times = {}

# --- Helpers -----------------------------------------------------------------

def get_payload(md_bytes):
    return next(iter(md_bytes.values()), b"")

def extract_illuminance(md_bytes):
    payload = get_payload(md_bytes)
    OFFSET = 8  # 10-2
    if len(payload) < OFFSET+2:
        return None
    raw = int.from_bytes(payload[OFFSET:OFFSET+2], "big") & 0x0FFF
    return ((raw-2047)*50+2000) if (raw>>11) else raw

def extract_env(md_bytes):
    payload = get_payload(md_bytes)
    OFF_HUM, OFF_INT, OFF_FRAC = 10, 9, 8
    if len(payload) < OFF_HUM+1:
        return None, None
    hum = payload[OFF_HUM] & 0x7F
    temp_int = payload[OFF_INT] & 0x7F
    frac = (payload[OFF_FRAC] & 0x07) / 10
    temp = temp_int + frac
    if not (payload[OFF_INT] & 0x80):
        temp = -temp
    return hum, temp

def extract_enocean(md_bytes):
    payload = get_payload(md_bytes)
    HUM_OFF, TEMP_HI, TEMP_LO, ILL_HI, ILL_LO = 8, 6, 5, 11, 10
    hum = payload[HUM_OFF] * 0.5
    temp = ((payload[TEMP_HI]<<8)|payload[TEMP_LO]) * 0.01
    illum = (payload[ILL_HI]<<8)|payload[ILL_LO]
    return hum, temp, illum

def post_to_elasticsearch(index, doc):
    """POST JSON to Elasticsearch index."""
    url = f"{ES_HOST}/{index}/_doc/"
    try:
        resp = requests.post(url, json=doc,
                             auth=(ES_USER, ES_PASSWORD),
                             timeout=5)
        resp.raise_for_status()
    except Exception as e:
        print(f"ES POST error ({index}): {e}", file=sys.stderr)

# --- Callback ---------------------------------------------------------------

def detection_callback(device, advertisement_data):
    raw_addr = device.address.replace(":", "").lower()
    cfg = DEVICE_CONFIG.get(raw_addr)
    if not cfg:
        return

    now = time.monotonic()
    last = last_emit_times.get(raw_addr, 0.0)
    if now - last < RATE_LIMIT_SECONDS:
        return
    last_emit_times[raw_addr] = now

    timestamp = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
    base = {"date": timestamp, "device": raw_addr}

    values = cfg["extractor"](advertisement_data.manufacturer_data)
    for field, val in zip(cfg["fields"], values):
        if val is None:
            continue
        doc = {**base, field: val}
        index_name = f"sensor-{field}"
        post_to_elasticsearch(index_name, doc)

# --- Main -------------------------------------------------------------------

async def run():
    scanner = BleakScanner(detection_callback=detection_callback)
    await scanner.start()
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        await scanner.stop()

if __name__ == "__main__":
    asyncio.run(run())
