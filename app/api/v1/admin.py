from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import require_roles
from app.models.agent_log import AgentAuditLog
from app.models.agent_log import FraudFlag, PricingSuggestion
from app.models.order import Order
from app.models.product import Product
from app.models.user import User
from app.agents.pricing import audit_product
from app.schemas.order import OrderResponse
from app.schemas.product import ProductResponse

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/orders", response_model=list[OrderResponse])
async def admin_orders(
    _: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
) -> list[Order]:
    result = await db.scalars(select(Order).order_by(Order.created_at.desc()))
    return list(result.all())


@router.post("/orders/{order_id}/verify-payment", response_model=OrderResponse)
async def verify_bank_payment(
    order_id: int,
    _: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
) -> Order:
    order = await db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.payment_method != "bank_transfer" or order.status != "awaiting_payment":
        raise HTTPException(status_code=409, detail="Order is not awaiting bank payment verification")
    order.payment_status = "paid"
    order.status = "confirmed"
    await db.commit()
    await db.refresh(order)
    return order


async def resolve_refund(refund_id: int, decision: str, db: AsyncSession) -> dict:
    refund = await db.get(AgentAuditLog, refund_id)
    if refund is None or refund.agent_name != "refund_agent":
        raise HTTPException(status_code=404, detail="Refund request not found")
    if refund.status != "pending_review":
        raise HTTPException(status_code=409, detail="Refund request has already been resolved")

    order = await db.get(Order, refund.order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    if decision == "approved":
        order.status = "refunded" if order.payment_status == "paid" else "return_approved"
        if order.payment_status == "paid":
            order.payment_status = "refunded"
    else:
        order.status = "confirmed"

    refund.status = decision
    refund.output_state = {**(refund.output_state or {}), "human_decision": decision}
    await db.commit()
    return {"status": decision, "order_id": order.id, "order_status": order.status, "payment_status": order.payment_status}


@router.get("/refunds")
async def pending_refunds(
    _: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    result = await db.scalars(
        select(AgentAuditLog)
        .where(AgentAuditLog.agent_name == "refund_agent", AgentAuditLog.status == "pending_review")
        .order_by(AgentAuditLog.created_at.desc())
    )
    refunds = []
    for refund in result.all():
        order = await db.get(Order, refund.order_id)
        if order is None:
            continue
        refunds.append(
            {
                "id": refund.id,
                "thread_id": refund.thread_id,
                "order_id": order.id,
                "order_number": order.order_number,
                "amount": order.final_amount,
                "order_status": order.status,
                "payment_status": order.payment_status,
                "customer_id": refund.user_id,
                "created_at": refund.created_at,
                "customer_reason": (refund.input_state or {}).get("user_message", ""),
                "ai_decision": (refund.output_state or {}).get("decision", "escalated"),
                "ai_note": (refund.output_state or {}).get("admin_note", ""),
            }
        )
    return refunds


@router.post("/refunds/{refund_id}/approve")
async def approve_refund(
    refund_id: int,
    _: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    return await resolve_refund(refund_id, "approved", db)


@router.post("/refunds/{refund_id}/reject")
async def reject_refund(
    refund_id: int,
    _: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    return await resolve_refund(refund_id, "rejected", db)


@router.get("/stats")
async def admin_stats(
    _: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    users = await db.scalar(select(func.count(User.id)))
    orders = await db.scalar(select(func.count(Order.id)))
    revenue = await db.scalar(select(func.coalesce(func.sum(Order.final_amount), 0)).where(Order.payment_status == "paid"))
    flagged = await db.scalar(select(func.count(FraudFlag.id)).where(FraudFlag.is_resolved.is_(False)))
    pending_refunds_count = await db.scalar(select(func.count(AgentAuditLog.id)).where(AgentAuditLog.agent_name == "refund_agent", AgentAuditLog.status == "pending_review"))
    return {"users": users or 0, "orders": orders or 0, "paid_revenue": revenue or 0, "open_fraud_flags": flagged or 0, "pending_refunds": pending_refunds_count or 0}


@router.get("/products", response_model=list[ProductResponse])
async def admin_products(
    _: User = Depends(require_roles("admin", "vendor")),
    db: AsyncSession = Depends(get_db),
) -> list[Product]:
    result = await db.scalars(select(Product).options(selectinload(Product.category)).order_by(Product.created_at.desc()))
    return list(result.all())


@router.post("/pricing-audit")
async def run_pricing_audit(
    _: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    products = list((await db.scalars(select(Product).where(Product.is_active.is_(True)))).all())
    suggestions = []
    for product in products:
        state = audit_product(product)
        suggestion = PricingSuggestion(**state)
        db.add(suggestion)
        suggestions.append(state)
    await db.commit()
    return suggestions


@router.get("/pricing-suggestions", response_model=None)
async def pricing_suggestions(
    _: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
) -> list[PricingSuggestion]:
    result = await db.scalars(select(PricingSuggestion).order_by(PricingSuggestion.created_at.desc()))
    return list(result.all())


@router.post("/pricing-suggestions/{suggestion_id}/apply")
async def apply_pricing_suggestion(
    suggestion_id: int,
    _: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    suggestion = await db.get(PricingSuggestion, suggestion_id)
    if suggestion is None:
        raise HTTPException(status_code=404, detail="Pricing suggestion not found")
    product = await db.get(Product, suggestion.product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    product.price = suggestion.suggested_price
    suggestion.is_applied = True
    await db.commit()
    return {"product_id": product.id, "price": product.price, "applied": True}


@router.get("/fraud/flags", response_model=None)
async def fraud_flags(
    _: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
) -> list[FraudFlag]:
    result = await db.scalars(select(FraudFlag).where(FraudFlag.is_resolved.is_(False)).order_by(FraudFlag.created_at.desc()))
    return list(result.all())


@router.post("/fraud/{order_id}/release")
async def release_fraud_order(
    order_id: int,
    _: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    order = await db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    flags = list((await db.scalars(select(FraudFlag).where(FraudFlag.order_id == order_id, FraudFlag.is_resolved.is_(False)))).all())
    for flag in flags:
        flag.is_resolved = True
    if order.status == "under_review":
        order.status = "confirmed"
    await db.commit()
    return {"order_id": order.id, "status": order.status, "released_flags": len(flags)}
