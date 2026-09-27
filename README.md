# Smart Event Planning Platform with Resource Coordination System

A self-contained, dependency-free implementation aligned to the supplied project presentation. It uses Python's standard library for the REST backend, SQLite for persistent relational storage, and responsive HTML/CSS/JavaScript for the frontend.

## Features
- Event planning and CRUD
- Resource catalog, allocation and same-date conflict detection
- Attendee profiles, registration and ticket codes
- QR-check-in workflow represented through ticket validation/check-in APIs
- Vendor onboarding and coordination data
- Budget, expenses and remaining-budget calculations
- Approval records and automation rules
- Notifications
- Reports and analytics
- Organizer profile/system health
- Foreign keys, constraints, indexes and seed data
- No external Python packages required

## Run on Windows
1. Install Python 3.10+.
2. Open PowerShell in this project folder.
3. Run `run.bat` or:
   `python backend/server.py`
4. Open `http://127.0.0.1:8000`

## Run on Linux/macOS
```bash
chmod +x run.sh
./run.sh
```

## API health check
Open `http://127.0.0.1:8000/api/health`.

## Database
The first startup creates `database/smart_event.db` from `schema.sql` and loads `seed.sql` only when the events table is empty.

## Important
The backend serves the frontend itself, so a second frontend server is not required. This avoids the common CORS/path mismatch that can happen when opening the HTML through a separate port.

## Project workflow
Plan/create event → allocate resources → register attendees → generate ticket → check in → assign vendors → manage budget/expenses → automation → reports/analytics.
