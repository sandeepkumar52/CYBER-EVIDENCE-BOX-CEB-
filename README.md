# Cyber Evidence Box (CEB)

CEB is a digital forensic evidence management and preservation platform. It allows authorized investigators to create cases, register digital evidence, verify cryptographic hashes, and track the chain of custody.

## Architecture

*   **Frontend**: React, TypeScript, Vite, React Router, Axios
*   **Backend**: Python, FastAPI, SQLAlchemy, Pydantic, Uvicorn
*   **Database**: SQLite (Development) / PostgreSQL-ready
*   **Authentication**: JWT (JSON Web Tokens) with bcrypt password hashing

## Project Structure

```
CAS Hardware/
├── frontend/             # React SPA
│   ├── src/              # Components, Context, Pages, Types
│   ├── package.json
│   └── vite.config.ts
├── Backend/              # FastAPI Application
│   ├── app/              # Core API Logic
│   │   ├── routers/      # API Endpoints
│   │   ├── hardware/     # Hardware Abstraction Layer
│   │   ├── models.py     # SQLAlchemy DB Models
│   │   └── main.py       # FastAPI Entrypoint
│   ├── storage/          # Secured File Storage for Evidence
│   └── requirements.txt
├── .gitignore
└── README.md
```

## Setup & Installation

### Backend

1.  Navigate to the `Backend` directory: `cd Backend`
2.  Create virtual environment: `python -m venv venv`
3.  Activate it: `.\venv\Scripts\activate` (Windows) or `source venv/bin/activate` (Mac/Linux)
4.  Install dependencies: `pip install -r requirements.txt`
5.  Run server: `uvicorn app.main:app --reload`
6.  *The server will start at http://localhost:8000. It automatically initializes the SQLite database with default users on first run.*

### Frontend

1.  Navigate to the `frontend` directory: `cd frontend`
2.  Install dependencies: `npm install`
3.  Run dev server: `npm run dev`
4.  *The frontend will start at http://localhost:5173.*

## Default Credentials

The system seeds the following users upon first initialization:

*   **Admin:** `admin` / `admin123`
*   **Investigator:** `investigator01` / `investigator123`

## Hardware Integration

CEB is designed to support hardware integration. The abstraction layer is available at `Backend/app/hardware`. A mock adapter is currently in use, exposing status via `GET /hardware/status`. When physical GPS/GNSS or controller boards are ready, a Serial adapter can seamlessly replace the mock implementation without affecting core logic.

## Security Considerations

*   Never commit `.env` or the `storage/` directory to source control.
*   The system uses SHA-256 for evidence hashing. A matching hash confirms data integrity but *does not independently establish legal admissibility without chain of custody documentation*.
*   Custody and audit logs are append-only.
