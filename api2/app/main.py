from __future__ import annotations

import os
from datetime import date, datetime
from decimal import Decimal
from collections.abc import Iterator

import httpx
from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import Date, DateTime, Integer, Numeric, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://study_user:study_pass@db2:5432/analytics_db")
SUBSCRIPTION_API_URL = os.getenv("SUBSCRIPTION_API_URL", "http://api1:8001")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


class BudgetTarget(Base):
    __tablename__ = "budget_targets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    month: Mapped[str] = mapped_column(String(7), unique=True, nullable=False)
    target_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)


class RecommendationHistory(Base):
    __tablename__ = "recommendation_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    message: Mapped[str] = mapped_column(Text, nullable=False)


class SubscriptionSnapshot(BaseModel):
    id: int
    name: str
    provider: str
    category: str
    price: float
    currency: str
    billing_cycle: str
    renewal_date: date | None
    status: str
    notes: str | None = None


class BudgetCreate(BaseModel):
    month: str
    target_amount: float


class BudgetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    month: str
    target_amount: float


class CategoryBreakdownRow(BaseModel):
    category: str
    monthly_total: float


class RecommendationRow(BaseModel):
    message: str


class TotalsRow(BaseModel):
    monthly_total: float
    yearly_total: float


app = FastAPI(title="Analytics API Service", version="1.0.0")


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
    return {"status": "ok", "service": "analytics-api"}


def fetch_subscriptions() -> list[SubscriptionSnapshot]:
    try:
        response = httpx.get(f"{SUBSCRIPTION_API_URL}/subscriptions", timeout=6.0)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail=f"Subscription service unavailable: {exc}") from exc

    payload = response.json()
    return [SubscriptionSnapshot(**item) for item in payload]


def monthly_equivalent(subscription: SubscriptionSnapshot) -> Decimal:
    amount = Decimal(str(subscription.price))
    if subscription.billing_cycle == "yearly":
        return (amount / Decimal("12")).quantize(Decimal("0.01"))
    return amount


@app.get("/analytics/monthly-total")
def monthly_total() -> dict[str, float]:
    subscriptions = fetch_subscriptions()
    total = sum(monthly_equivalent(item) for item in subscriptions if item.status == "active")
    return {"monthly_total": float(total)}


@app.get("/analytics/yearly-total")
def yearly_total() -> dict[str, float]:
    subscriptions = fetch_subscriptions()
    monthly_total_value = sum(monthly_equivalent(item) for item in subscriptions if item.status == "active")
    return {"yearly_total": float((monthly_total_value * Decimal("12")).quantize(Decimal("0.01")))}


@app.get("/analytics/totals", response_model=TotalsRow)
def totals() -> TotalsRow:
    subscriptions = fetch_subscriptions()
    monthly_total_value = sum(monthly_equivalent(item) for item in subscriptions if item.status == "active")
    yearly_total_value = (monthly_total_value * Decimal("12")).quantize(Decimal("0.01"))
    return TotalsRow(monthly_total=float(monthly_total_value), yearly_total=float(yearly_total_value))


@app.get("/analytics/category-breakdown", response_model=list[CategoryBreakdownRow])
def category_breakdown() -> list[CategoryBreakdownRow]:
    subscriptions = fetch_subscriptions()
    buckets: dict[str, Decimal] = {}
    for item in subscriptions:
        if item.status != "active":
            continue
        key = item.category.strip().lower() or "other"
        buckets[key] = buckets.get(key, Decimal("0.00")) + monthly_equivalent(item)

    return [
        CategoryBreakdownRow(category=category, monthly_total=float(total.quantize(Decimal("0.01"))))
        for category, total in sorted(buckets.items(), key=lambda pair: pair[1], reverse=True)
    ]


@app.get("/analytics/upcoming-costs")
def upcoming_costs() -> dict[str, list[dict[str, str | float | None]]]:
    subscriptions = fetch_subscriptions()
    today = date.today()
    upcoming = [item for item in subscriptions if item.renewal_date is not None and item.renewal_date >= today]
    upcoming.sort(key=lambda item: item.renewal_date)
    return {
        "upcoming": [
            {
                "name": item.name,
                "provider": item.provider,
                "renewal_date": item.renewal_date.isoformat() if item.renewal_date else None,
                "amount": float(monthly_equivalent(item)),
            }
            for item in upcoming[:10]
        ]
    }


@app.post("/analytics/budget", response_model=BudgetRead, status_code=status.HTTP_201_CREATED)
def upsert_budget(payload: BudgetCreate, db: Session = Depends(get_db)) -> BudgetTarget:
    budget = db.query(BudgetTarget).filter(BudgetTarget.month == payload.month).first()
    if budget is None:
        budget = BudgetTarget(month=payload.month, target_amount=payload.target_amount)
    else:
        budget.target_amount = payload.target_amount

    db.add(budget)
    db.commit()
    db.refresh(budget)
    return budget


@app.get("/analytics/budget-status")
def budget_status(db: Session = Depends(get_db)) -> dict[str, str | float | None]:
    month = date.today().strftime("%Y-%m")
    budget = db.query(BudgetTarget).filter(BudgetTarget.month == month).first()
    subscriptions = fetch_subscriptions()
    monthly_total_value = sum(monthly_equivalent(item) for item in subscriptions if item.status == "active")

    if budget is None:
        return {
            "month": month,
            "target_amount": None,
            "monthly_total": float(monthly_total_value),
            "status": "no-budget",
            "difference": None,
        }

    diff = Decimal(str(budget.target_amount)) - monthly_total_value
    return {
        "month": month,
        "target_amount": float(budget.target_amount),
        "monthly_total": float(monthly_total_value),
        "status": "under-budget" if diff >= 0 else "over-budget",
        "difference": float(diff.quantize(Decimal("0.01"))),
    }


@app.get("/analytics/recommendations", response_model=list[RecommendationRow])
def recommendations(db: Session = Depends(get_db)) -> list[RecommendationRow]:
    subscriptions = fetch_subscriptions()
    sorted_by_cost = sorted(
        [item for item in subscriptions if item.status == "active"],
        key=monthly_equivalent,
        reverse=True,
    )

    messages: list[str] = []
    if sorted_by_cost:
        top = sorted_by_cost[0]
        messages.append(f"Review '{top.name}' from {top.provider}; it has the highest monthly impact.")

    categories: dict[str, int] = {}
    for item in sorted_by_cost:
        key = item.category.strip().lower() or "other"
        categories[key] = categories.get(key, 0) + 1

    duplicated = [name for name, count in categories.items() if count > 1]
    if duplicated:
        messages.append(f"You have multiple services in categories: {', '.join(duplicated[:3])}.")

    if not messages:
        messages.append("No active subscriptions to analyze yet. Add subscriptions first.")

    for message in messages:
        db.add(RecommendationHistory(message=message))
    db.commit()

    return [RecommendationRow(message=message) for message in messages]


@app.get("/analytics/recommendation-history")
def recommendation_history(db: Session = Depends(get_db)) -> dict[str, list[dict[str, str]]]:
    rows = db.query(RecommendationHistory).order_by(RecommendationHistory.generated_at.desc()).limit(20).all()
    return {
        "history": [
            {"generated_at": item.generated_at.isoformat(), "message": item.message}
            for item in rows
        ]
    }
