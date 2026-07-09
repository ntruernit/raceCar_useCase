# Race Car Demo — From Track to WatsonX

Live demo built for IBM Innovation Day. A physical slot car race emits MQTT events that flow through Confluent Cloud (Kafka + Flink), get exposed as a REST API on IBM Code Engine, and are consumed by a WatsonX Orchestrate agent that answers race questions in natural language.

## Architecture

```
Slot Car Track (Cockpit-XP)
     │  MQTT events (lap times, fuel %, position)
     ▼
bridge.py  (Windows)
     │  produces to Kafka
     ▼
Confluent Cloud
     │  Kafka topic: race-events
     │  Flink: continuous stream processing
     ▼
FastAPI on IBM Code Engine
     │  GET /standings, /lap-history, /fuel-alerts
     ▼
IBM WatsonX Orchestrate
     │  Agent: race_strategist
     ▼
Natural language answers to race questions
```

## Repository layout

```
.
├── bridge.py              MQTT → Confluent Kafka producer (runs on Windows)
├── api/
│   ├── api.py             FastAPI app: consumes Kafka, exposes REST endpoints
│   └── requirements.txt
├── Dockerfile             Container definition for the API
├── agent/
│   ├── openapi.yaml       OpenAPI spec of the REST API (tool definitions)
│   └── race_strategist.yaml   WatsonX Orchestrate agent definition
├── deploy.sh              Build image → push to Docker Hub → deploy to Code Engine
├── deploy_agent.sh        Import tools and deploy the WatsonX Orchestrate agent
├── presentation/
│   └── slides.md          Presentation deck
└── .env.template          Required environment variables
```

## Prerequisites

- Docker Desktop
- IBM Cloud CLI (`ibmcloud`) with the Code Engine plugin
- Python 3.11+ with a virtual environment at `.venv`
- A Confluent Cloud cluster with a `race-events` topic (6 partitions)
- Docker Hub account (or any container registry)
- IBM WatsonX Orchestrate instance
- A Windows machine running the Cockpit-XP slot car software with its MQTT broker on `localhost:1883`

## Setup

```bash
cp .env.template .env
# Fill in Confluent, Docker Hub, Code Engine, and WatsonX Orchestrate values
```

Install the Python dependencies for local tooling (WatsonX Orchestrate ADK, etc.):

```bash
python -m venv .venv
.venv/bin/pip install ibm-watsonx-orchestrate
```

## Running the bridge (Windows)

The bridge is what forwards MQTT events from the race software into Confluent.

```bash
pip install -r requirements.txt
python bridge.py
```

Or run the pre-built `bridge.exe` (built with PyInstaller from `bridge.py`).

## Deploying the API to Code Engine

```bash
./deploy.sh
```

This builds the container for `linux/amd64`, pushes to Docker Hub, and creates or updates the Code Engine app with the Confluent credentials injected as environment variables.

## Deploying the agent to WatsonX Orchestrate

Activate the target environment first (needs interactive login for the API key):

```bash
source .venv/bin/activate
orchestrate env activate RACE
```

Then run:

```bash
./deploy_agent.sh
```

This imports the OpenAPI tools, imports the agent definition, and deploys it.

## API endpoints

Once deployed, the FastAPI app exposes:

- `GET /health` — health check
- `GET /standings` — current race leaderboard with best lap and fuel per car
- `GET /lap-history` — every individual lap for every car
- `GET /fuel-alerts` — events where a car dropped below 25% fuel

## What the agent can answer

- Who is winning the race?
- Who has set the fastest lap?
- Which cars are at risk of running out of fuel?
- Is car X getting faster or slower over time?
- Which car has been most consistent?
- What is the average lap time for each car?
