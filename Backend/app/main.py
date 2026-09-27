from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from .config import CORS_ORIGINS
from .database import Base, engine, SessionLocal
from .models import User
from .routers import audit, auth, cases, custody, dashboard, evidence, users, hardware
from .security.auth import hash_password, verify_password


def init_db():
    Base.metadata.create_all(bind=engine)

    # Schema migration check for SQLite dev environment
    try:
        inspector = inspect(engine)
        if "users" in inspector.get_table_names():
            columns = [col["name"] for col in inspector.get_columns("users")]
            if "hashed_password" not in columns:
                with engine.begin() as conn:
                    conn.execute(text("ALTER TABLE users ADD COLUMN hashed_password VARCHAR(255)"))
                    print("[CEB] Migrated table 'users': added 'hashed_password' column.")

        if "cases" in inspector.get_table_names():
            case_columns = [col["name"] for col in inspector.get_columns("cases")]
            if "is_archived" not in case_columns:
                with engine.begin() as conn:
                    conn.execute(text("ALTER TABLE cases ADD COLUMN is_archived BOOLEAN DEFAULT 0"))
                    print("[CEB] Migrated table 'cases': added 'is_archived' column.")

        if "evidence" in inspector.get_table_names():
            ev_columns = [col["name"] for col in inspector.get_columns("evidence")]
            if "file_size_bytes" not in ev_columns:
                with engine.begin() as conn:
                    conn.execute(text("ALTER TABLE evidence ADD COLUMN file_size_bytes INTEGER"))
                    print("[CEB] Migrated table 'evidence': added 'file_size_bytes' column.")

        # Create/ensure initial seed users with valid hashed passwords
        db: Session = SessionLocal()
        try:
            admin_user = db.query(User).filter(User.username == "admin").first()
            if not admin_user:
                admin_user = User(
                    username="admin",
                    role="Admin",
                    hashed_password=hash_password("admin123"),
                )
                db.add(admin_user)
            elif not verify_password("admin123", admin_user.hashed_password):
                admin_user.hashed_password = hash_password("admin123")

            inv_user = db.query(User).filter(User.username == "investigator01").first()
            if not inv_user:
                inv_user = User(
                    username="investigator01",
                    role="Investigator",
                    hashed_password=hash_password("investigator123"),
                )
                db.add(inv_user)
            elif not verify_password("investigator123", inv_user.hashed_password):
                inv_user.hashed_password = hash_password("investigator123")

            db.commit()
        finally:
            db.close()
    except Exception as e:
        print(f"[CEB] DB Init Note: {e}")


# Run initialization on import
init_db()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Cyber Evidence Box (CEB) API",
    description="Digital Forensic Evidence Management Platform Backend API",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS if CORS_ORIGINS != ["*"] else ["*"],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(cases.router)
app.include_router(evidence.router)
app.include_router(custody.router)
app.include_router(audit.router)
app.include_router(dashboard.router)
app.include_router(hardware.router)


@app.get("/", tags=["System"])
def root():
    return {
        "message": "Cyber Evidence Box (CEB) API",
        "status": "online",
        "version": "0.2.0",
        "docs": "/docs",
    }


@app.get("/health", tags=["System"])
def health_check():
    return {
        "status": "healthy",
        "system": "Cyber Evidence Box",
    }