import json
import os
from datetime import datetime, timezone
from pathlib import Path

import certifi
import paho.mqtt.client as mqtt
from confluent_kafka import Producer
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

CONFLUENT_BOOTSTRAP_SERVERS = os.environ["CONFLUENT_BOOTSTRAP_SERVERS"]
CONFLUENT_API_KEY = os.environ["CONFLUENT_API_KEY"]
CONFLUENT_API_SECRET = os.environ["CONFLUENT_API_SECRET"]
KAFKA_TOPIC = os.environ.get("KAFKA_TOPIC", "race-events")
MQTT_HOST = os.environ.get("MQTT_HOST", "localhost")
MQTT_PORT = int(os.environ.get("MQTT_PORT", 1883))

producer = Producer({
    "bootstrap.servers": CONFLUENT_BOOTSTRAP_SERVERS,
    "security.protocol": "SASL_SSL",
    "sasl.mechanism": "PLAIN",
    "sasl.username": CONFLUENT_API_KEY,
    "sasl.password": CONFLUENT_API_SECRET,
    "ssl.ca.location": certifi.where(),
})


def on_delivery(err, msg):
    if err:
        print(f"[ERROR] Delivery failed for {msg.topic()}: {err}")
    else:
        print(f"[OK] {msg.topic()} partition={msg.partition()} offset={msg.offset()}")


def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print(f"[MQTT] Connected to broker at {MQTT_HOST}:{MQTT_PORT}")
        client.subscribe("addon/#")
        print("[MQTT] Subscribed to addon/#")
    else:
        print(f"[MQTT] Connection failed with code {reason_code}")


def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        payload = {"raw": msg.payload.decode("utf-8", errors="replace")}

    print(f"[MQTT] topic={msg.topic} values={json.dumps(payload, ensure_ascii=False)}")

    event = {
        "mqtt_topic": msg.topic,
        "event_type": msg.topic.split("/")[-1],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": payload,
    }

    producer.produce(
        KAFKA_TOPIC,
        key=event["event_type"],
        value=json.dumps(event),
        callback=on_delivery,
    )
    producer.poll(0)
    print(f"[BRIDGE] {event['event_type']} → {KAFKA_TOPIC}")


def main():
    print("=== Race Car MQTT → Confluent Bridge ===")
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    except ConnectionRefusedError as exc:
        print(f"[MQTT] Unable to connect to {MQTT_HOST}:{MQTT_PORT}.")
        print("[MQTT] Check that the broker is running and that MQTT_HOST/MQTT_PORT are correct.")
        print(f"[MQTT] {exc}")
        return
    except OSError as exc:
        print(f"[MQTT] Connection error while reaching {MQTT_HOST}:{MQTT_PORT}.")
        print("[MQTT] Check network access, broker status, and any local firewall rules.")
        print(f"[MQTT] {exc}")
        return

    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("\n[BRIDGE] Shutting down...")
    finally:
        print("[BRIDGE] Flushing remaining messages...")
        producer.flush(timeout=10)
        client.disconnect()


if __name__ == "__main__":
    main()
