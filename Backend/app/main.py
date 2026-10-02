import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from .config import CORS_ORIGINS
from .database import Base, engine, SessionLocal
from .models import User
from .routers import audit, auth, cases, custody, dashboard, evidence, hardware, storage, users
from .security.auth import hash_password, verify_password
from .services.usb_service import usb_service
from .hardware.usb.usb_manager import usb_manager
from .hardware.usb.usb_events import hardware_events
from .hardware.storage.storage_manager import storage_manager
from .websocket_manager import ws_manager

logger = logging.getLogger("ceb.main")


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

    # Pass the running event loop to the hardware events dispatcher
    hardware_events.set_loop(asyncio.get_running_loop())

    # Start forensic USB monitor
    usb_service.start_monitoring()

    # Start USB serial and storage managers
    try:
        await usb_manager.start()
    except Exception as e:
        logger.error(f"Error starting USB serial manager: {e}")

    try:
        await storage_manager.start()
    except Exception as e:
        logger.error(f"Error starting USB storage manager: {e}")

    yield

    # Clean shutdown
    try:
        await storage_manager.stop()
    except Exception as e:
        logger.debug(f"Error stopping storage manager: {e}")

    try:
        await usb_manager.stop()
    except Exception as e:
        logger.debug(f"Error stopping USB manager: {e}")

    usb_service.stop_monitoring()


app = FastAPI(
    title="Cyber Evidence Box (CEB) API",
    description="Digital Forensic Evidence Management Platform Backend API with Integrated USB Subsystem",
    version="0.3.0",
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
app.include_router(hardware.router, prefix="/api")
app.include_router(storage.router)
app.include_router(storage.router, prefix="/api")


@app.get("/", tags=["System"])
def root():
    return {
        "message": "Cyber Evidence Box (CEB) API",
        "status": "online",
        "version": "0.3.0",
        "docs": "/docs",
    }


@app.get("/health", tags=["System"])
@app.get("/api/health", tags=["System"])
def health_check():
    db_ok = True
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        logger.error(f"[DATABASE][ERROR] Health check failed: {e}")
        db_ok = False

    usb_info = usb_manager.get_health()
    from datetime import datetime, timezone
    return {
        "status": "healthy" if db_ok else "degraded",
        "service": "Cyber Evidence Box (CEB) Backend",
        "system": "Cyber Evidence Box",
        "database": db_ok,
        "usb_service": usb_info.get("system") == "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "hardware": usb_info,
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive & handle incoming pings
            msg = await websocket.receive_text()
            if msg == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)