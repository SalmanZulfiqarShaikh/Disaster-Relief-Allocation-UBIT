# Disaster Relief Resource Allocation & Routing Network

BSCS — 4th Semester (Evening)

## Team

- Muhammad Fasih Dagia — EB25210006055
- Muhammad Salman — EB25210006070
- Muhammad Bin Abu Muhammad — EB25210006053
- Syed Muhammad Hussain Abbas — EB25210006096

Presented to: Sir Faiz and Ma'am Ilsa Naeem

## Overview

During floods, fires, and building collapses, people send messages to whoever they can reach, and most of those messages never reach someone who can act. This system takes those messages, works out who needs help first, and passes each case to a responder with everything they need.

A person messages a WhatsApp number in English, Urdu, Roman Urdu, or a mix. The system:

- Sends safety steps and the official emergency number straight away, before any other processing.
- Extracts the category (flood, fire, medical, trapped, structural), the urgency, and the location from the message.
- Merges reports from the same area into one incident, so duplicate messages do not create duplicate work.
- Scores each case with a deterministic priority formula and a plain-language reason.
- Lets a coordinator review the queue on a live dashboard with a map and approve the dispatch.
- Offers the case to the nearest on-duty volunteers, escalates to the next ring if nobody accepts in time, and records each step as an event.
- Checks back with the original reporter when a case is marked done.

The web interface is branded SafeZone.

## Scope and limits

- The system does not rescue anyone and is not an emergency service. Fire and medical cases always show the official emergency number first.
- Volunteers in this prototype are demo accounts. They are not vetted or trained.
- Responders receive a link with the case details. There is no live integration with any organisation's systems.
- The system covers 78 areas across the seven districts of Karachi. Area positions are approximate.

## Technology

- Backend: Python 3.11+, FastAPI, Microsoft SQL Server (T-SQL), pyodbc, WhatsApp Cloud API
- Frontend: React 19, TypeScript, Vite, Tailwind CSS v4, Server-Sent Events
- Deployment: Docker

## Repository layout

- `Backend/`: FastAPI application, services, routes, database schema (`data/schema.sql`), and tests
- `Frontend/`: control room and public pages
- `docs/`: deployment notes

## Database setup

1. Create the database and tables by running `Backend/data/schema.sql` in SQL Server Management Studio.
2. Set `SQLSERVER_CONNECTION_STRING` in your `.env` file. Example:

   ```
   Driver={ODBC Driver 18 for SQL Server};Server=localhost;Database=safezone;Trusted_Connection=yes;Encrypt=yes;TrustServerCertificate=yes;
   ```

3. Seed the zones and demo volunteers:

   ```
   cd Backend
   python -m data.seed
   ```

## Running locally

Create a `.env` file at the repository root from `.env.example` and fill in the database connection string and WhatsApp settings.

Backend:

```
cd Backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Frontend:

```
cd Frontend
npm install
npm run dev
```

The frontend dev server runs on port 5173 and forwards `/api` requests to the backend on port 8000.

## Tests

```
cd Backend
python -m pytest -q
```

The test suite runs offline, with no network access, database, or API keys.

## Utilities

```
python -m scripts.hash_password      # hash a control room password
python -m scripts.build_localities   # rebuild the OpenStreetMap locality data
python -m scripts.verify_setup       # check configuration and database tables
```

## Attribution

Locality and boundary data © OpenStreetMap contributors, available under the Open Database License (ODbL).
