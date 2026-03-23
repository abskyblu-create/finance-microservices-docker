from __future__ import annotations

import os
from datetime import date
from enum import Enum
from collections.abc import Iterator

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict
from sqlalchemy import Date, Enum as SQLEnum, Integer, Numeric, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://study_user:study_pass@db1:5432/subscriptions_db",
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


class BillingCycle(str, Enum):
    monthly = "monthly"
    yearly = "yearly"


class SubscriptionStatus(str, Enum):
    active = "active"
    paused = "paused"
    canceled = "canceled"


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    provider: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[str] = mapped_column(String(80), nullable=False)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="EUR")
    billing_cycle: Mapped[BillingCycle] = mapped_column(
        SQLEnum(BillingCycle), default=BillingCycle.monthly
    )
    renewal_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[SubscriptionStatus] = mapped_column(
        SQLEnum(SubscriptionStatus), default=SubscriptionStatus.active
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class SubscriptionCreate(BaseModel):
    name: str
    provider: str
    category: str
    price: float
    currency: str = "EUR"
    billing_cycle: BillingCycle = BillingCycle.monthly
    renewal_date: date | None = None
    status: SubscriptionStatus = SubscriptionStatus.active
    notes: str | None = None


class SubscriptionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    provider: str
    category: str
    price: float
    currency: str
    billing_cycle: BillingCycle
    renewal_date: date | None
    status: SubscriptionStatus
    notes: str | None


app = FastAPI(title="Subscription Manager Service", version="1.0.0")

# ✅ CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/subscriptions", response_model=list[SubscriptionRead])
def list_subscriptions(db: Session = Depends(get_db)):
    return db.query(Subscription).order_by(Subscription.id.desc()).all()


@app.post("/subscriptions", response_model=SubscriptionRead)
def create_subscription(payload: SubscriptionCreate, db: Session = Depends(get_db)):
    subscription = Subscription(**payload.model_dump())
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    return subscription


@app.delete("/subscriptions/{subscription_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subscription(subscription_id: int, db: Session = Depends(get_db)):
    subscription = db.get(Subscription, subscription_id)
    if subscription is None:
        raise HTTPException(status_code=404, detail="Subscription not found")

    db.delete(subscription)
    db.commit()