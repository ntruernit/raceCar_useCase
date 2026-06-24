import certifi
import json
import os
import threading
from collections import deque

from confluent_kafka import Consumer
from fastapi import FastAPI

BOOTSTRAP_SERVERS = os.environ["CONFLUENT_BOOTSTRAP_SERVERS"]
API_KEY = os.environ["CONFLUENT_API_KEY"]
API_SECRET = os.environ["CONFLUENT_API_SECRET"]

_standings = {}
_fuel_alerts = deque(maxlen=50)
_lap_history = []

app = FastAPI(title="Race API")


def _make_consumer():
    return Consumer({
        "bootstrap.servers": BOOTSTRAP_SERVERS,
        "security.protocol": "SASL_SSL",
        "sasl.mechanism": "PLAIN",
        "sasl.username": API_KEY,
        "sasl.password": API_SECRET,
        "ssl.ca.location": certifi.where(),
        "group.id": "race-api",
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False,
    })


def _consume():
    consumer = _make_consumer()
    consumer.subscribe(["race-events"])
    while True:
        msg = consumer.poll(0.1)
        if msg is None or msg.error():
            continue
        try:
            event = json.loads(msg.value().decode("utf-8"))
            if event.get("event_type") != "evStartZiel":
                continue
            p = event.get("payload", {})
            car_id = p.get("slot")
            if not car_id:
                continue

            lap = int(p.get("runde", 0))
            lap_time = float(p.get("rundenzeit", 0))
            fuel = float(p.get("tankstand", 100))
            position = p.get("position")

            current = _standings.get(car_id, {
                "car_id": car_id,
                "total_laps": 0,
                "best_lap_ms": None,
                "latest_fuel_pct": 100.0,
                "latest_position": None,
            })
            if lap > current["total_laps"]:
                current["total_laps"] = lap
                _lap_history.append({
                    "car_id": car_id,
                    "lap": lap,
                    "lap_time_ms": lap_time,
                    "fuel_pct": fuel,
                    "position": position,
                    "timestamp": event.get("timestamp"),
                })
            if lap_time > 0:
                if current["best_lap_ms"] is None or lap_time < current["best_lap_ms"]:
                    current["best_lap_ms"] = lap_time
            current["latest_fuel_pct"] = fuel
            current["latest_position"] = position
            _standings[car_id] = current

            if fuel < 25.0:
                _fuel_alerts.appendleft({
                    "car_id": car_id,
                    "fuel_pct": fuel,
                    "at_lap": lap,
                    "event_time": event.get("timestamp"),
                })
        except Exception as e:
            print(f"[CONSUMER] Error: {e}")


threading.Thread(target=_consume, daemon=True).start()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/standings")
def get_standings():
    return sorted(_standings.values(), key=lambda x: x["total_laps"], reverse=True)


@app.get("/fuel-alerts")
def get_fuel_alerts():
    return list(_fuel_alerts)


@app.get("/lap-history")
def get_lap_history():
    return sorted(_lap_history, key=lambda x: (x["car_id"], x["lap"]))
