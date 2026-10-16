from typing import Optional
from sqlalchemy import String, Text, Numeric, Integer, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin


class AgentAuditLog(Base, TimestampMixin):
    __tablename__ = "agent_audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    agent_name: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    thread_id: Mapped[Optional[str]] = mapped_column(String(255), index=True, nullable=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    order_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False)  # success, escalated, failed, pending_review
    input_state: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    output_state: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    execution_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class PricingSuggestion(Base, TimestampMixin):
    __tablename__ = "pricing_suggestions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    current_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    suggested_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    competitor_price: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False)  # raise, lower, keep
    confidence: Mapped[float] = mapped_column(Numeric(3, 2), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    is_applied: Mapped[bool] = mapped_column(default=False, nullable=False)


class FraudFlag(Base, TimestampMixin):
    __tablename__ = "fraud_flags"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    fraud_score: Mapped[int] = mapped_column(Integer, nullable=False)
    verdict: Mapped[str] = mapped_column(String(50), nullable=False)  # Safe, Flagged
    flags: Mapped[Optional[list]] = mapped_column(JSON, default=list, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_resolved: Mapped[bool] = mapped_column(default=False, nullable=False)
    admin_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
