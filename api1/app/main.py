from __future__ import annotations

import os
from datetime import date
from enum import Enum
from collections.abc import Iterator

from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import Date, Enum as SQLEnum, Integer, Numeric, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://study_user:study_pass@db1:5432/subscriptions_db")

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
    billing_cycle: Mapped[BillingCycle] = mapped_column(SQLEnum(BillingCycle), default=BillingCycle.monthly)
    renewal_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[SubscriptionStatus] = mapped_column(SQLEnum(SubscriptionStatus), default=SubscriptionStatus.active)
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


class SubscriptionUpdate(BaseModel):
    name: str | None = None
    provider: str | None = None
    category: str | None = None
    price: float | None = None
    currency: str | None = None
    billing_cycle: BillingCycle | None = None
    renewal_date: date | None = None
    status: SubscriptionStatus | None = None
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


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "subscription-manager"}


@app.get("/subscriptions", response_model=list[SubscriptionRead])
def list_subscriptions(db: Session = Depends(get_db)) -> list[Subscription]:
    return db.query(Subscription).order_by(Subscription.id.desc()).all()


@app.get("/subscriptions/{subscription_id}", response_model=SubscriptionRead)
def get_subscription(subscription_id: int, db: Session = Depends(get_db)) -> Subscription:
    subscription = db.get(Subscription, subscription_id)
    if subscription is None:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return subscription


@app.post("/subscriptions", response_model=SubscriptionRead, status_code=status.HTTP_201_CREATED)
def create_subscription(payload: SubscriptionCreate, db: Session = Depends(get_db)) -> Subscription:
    subscription = Subscription(**payload.model_dump())
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    return subscription


@app.put("/subscriptions/{subscription_id}", response_model=SubscriptionRead)
def update_subscription(subscription_id: int, payload: SubscriptionUpdate, db: Session = Depends(get_db)) -> Subscription:
    subscription = db.get(Subscription, subscription_id)
    if subscription is None:
        raise HTTPException(status_code=404, detail="Subscription not found")

    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(subscription, key, value)

    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    return subscription


@app.patch("/subscriptions/{subscription_id}/status", response_model=SubscriptionRead)
def patch_subscription_status(subscription_id: int, new_status: SubscriptionStatus, db: Session = Depends(get_db)) -> Subscription:
    subscription = db.get(Subscription, subscription_id)
    if subscription is None:
        raise HTTPException(status_code=404, detail="Subscription not found")

    subscription.status = new_status
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    return subscription


@app.get("/subscriptions/upcoming-renewals", response_model=list[SubscriptionRead])
def upcoming_renewals(db: Session = Depends(get_db)) -> list[Subscription]:
    today = date.today()
    return (
        db.query(Subscription)
        .filter(Subscription.renewal_date.is_not(None))
        .filter(Subscription.renewal_date >= today)
        .order_by(Subscription.renewal_date.asc())
        .all()
    )


@app.delete("/subscriptions/{subscription_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subscription(subscription_id: int, db: Session = Depends(get_db)) -> None:
    subscription = db.get(Subscription, subscription_id)
    if subscription is None:
        raise HTTPException(status_code=404, detail="Subscription not found")

    db.delete(subscription)
    db.commit()
