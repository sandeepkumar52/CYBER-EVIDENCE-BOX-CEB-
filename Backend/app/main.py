from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from . import models
from .database import Base, engine, get_db
from .schemas import (
    CaseCreate,
    CaseResponse,
    UserCreate,
    UserResponse,
)

Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="Cyber Evidence Box API",
    description="Backend API for the Cyber Evidence Box forensic platform",
    version="0.1.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "message": "Cyber Evidence Box API",
        "status": "online",
        "version": "0.1.0",
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
    }


@app.post("/cases", response_model=CaseResponse)
def create_case(
    case: CaseCreate,
    db: Session = Depends(get_db),
):
    existing_case = (
        db.query(models.Case)
        .filter(models.Case.case_id == case.case_id)
        .first()
    )

    if existing_case:
        raise HTTPException(
            status_code=400,
            detail="Case ID already exists",
        )

    new_case = models.Case(
        case_id=case.case_id,
        case_name=case.case_name,
        description=case.description,
        status=case.status,
        created_by=case.created_by,
    )

    db.add(new_case)
    db.commit()
    db.refresh(new_case)

    return new_case


@app.get("/cases", response_model=list[CaseResponse])
def get_cases(
    db: Session = Depends(get_db),
):
    cases = (
        db.query(models.Case)
        .order_by(models.Case.created_at.desc())
        .all()
    )

    return cases


@app.get("/cases/{case_id}", response_model=CaseResponse)
def get_case(
    case_id: str,
    db: Session = Depends(get_db),
):
    case = (
        db.query(models.Case)
        .filter(models.Case.case_id == case_id)
        .first()
    )

    if not case:
        raise HTTPException(
            status_code=404,
            detail="Case not found",
        )

    return case

@app.post("/users", response_model=UserResponse)
def create_user(
    user: UserCreate,
    db: Session = Depends(get_db),
):
    existing_user = (
        db.query(models.User)
        .filter(models.User.username == user.username)
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Username already exists",
        )

    new_user = models.User(
        username=user.username,
        role=user.role,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


@app.get("/users", response_model=list[UserResponse])
def get_users(
    db: Session = Depends(get_db),
):
    return (
        db.query(models.User)
        .order_by(models.User.created_at.desc())
        .all()
    )