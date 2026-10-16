from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import String, Text, Numeric, Integer, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.address import Address
    from app.models.product import Product


class Order(Base, TimestampMixin):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    order_number: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    shipping_address_id: Mapped[Optional[int]] = mapped_column(ForeignKey("addresses.id", ondelete="SET NULL"), nullable=True)
    
    total_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    discount_amount: Mapped[float] = mapped_column(Numeric(10, 2), default=0.0, nullable=False)
    final_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    # Status: awaiting_payment, confirmed, under_review, shipped, delivered, cancelled, refunded
    status: Mapped[str] = mapped_column(String(50), default="awaiting_payment", nullable=False)
    
    # Payment fields (strictly bank_transfer or cod)
    payment_method: Mapped[str] = mapped_column(String(50), nullable=False)  # bank_transfer | cod
    # pending_verification, pending_on_delivery, paid, refunded, failed
    payment_status: Mapped[str] = mapped_column(String(50), default="pending_verification", nullable=False)
    payment_reference_code: Mapped[Optional[str]] = mapped_column(String(100), unique=True, index=True, nullable=True)
    bank_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Fraud & Promo tracking
    fraud_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    fraud_flags: Mapped[Optional[list]] = mapped_column(JSON, default=list, nullable=True)
    promo_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", back_populates="orders")
    shipping_address: Mapped[Optional["Address"]] = relationship("Address")
    items: Mapped[List["OrderItem"]] = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base, TimestampMixin):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[Optional[int]] = mapped_column(ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    subtotal: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    order: Mapped["Order"] = relationship("Order", back_populates="items")
    product: Mapped[Optional["Product"]] = relationship("Product", back_populates="order_items")
