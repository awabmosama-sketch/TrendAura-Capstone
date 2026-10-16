from datetime import datetime, timezone
from decimal import Decimal
from secrets import token_hex

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.agents.refund import run_refund_agent
from app.api.v1.agents import create_fraud_flag
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.address import Address
from app.models.cart import Cart, CartItem
from app.models.agent_log import AgentAuditLog
from app.models.order import Order, OrderItem
from app.models.user import User
from app.schemas.order import CheckoutRequest, CheckoutResponse, OrderResponse, ReturnRequest

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("/checkout", response_model=CheckoutResponse, status_code=status.HTTP_201_CREATED)
async def checkout(
    payload: CheckoutRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CheckoutResponse:
    cart = await db.scalar(
        select(Cart).options(selectinload(Cart.items).selectinload(CartItem.product)).where(Cart.user_id == user.id)
    )
    if cart is None or not cart.items:
        raise HTTPException(status_code=400, detail="Your cart is empty")

    for item in cart.items:
        if not item.product.is_active or item.product.stock_quantity < item.quantity:
            raise HTTPException(status_code=409, detail=f"Product unavailable: {item.product.name}")

    total = sum((Decimal(item.product.price) * item.quantity for item in cart.items), Decimal("0"))
    address = Address(user_id=user.id, **payload.shipping_address.model_dump())
    db.add(address)
    await db.flush()

    is_bank_transfer = payload.payment_method == "bank_transfer"
    reference = None
    if is_bank_transfer:
        reference = f"TRX-BT-{datetime.now(timezone.utc):%Y%m%d}-{token_hex(3).upper()}"

    order = Order(
        order_number=f"TRX-{datetime.now(timezone.utc):%Y%m%d}-{token_hex(4).upper()}",
        user_id=user.id,
        shipping_address_id=address.id,
        total_amount=total,
        discount_amount=Decimal("0"),
        final_amount=total,
        status="awaiting_payment" if is_bank_transfer else "confirmed",
        payment_method=payload.payment_method,
        payment_status="pending_verification" if is_bank_transfer else "pending_on_delivery",
        payment_reference_code=reference,
    )
    db.add(order)
    await db.flush()

    for cart_item in cart.items:
        product = cart_item.product
        product.stock_quantity -= cart_item.quantity
        db.add(
            OrderItem(
                order_id=order.id,
                product_id=product.id,
                product_name=product.name,
                unit_price=product.price,
                quantity=cart_item.quantity,
                subtotal=Decimal(product.price) * cart_item.quantity,
            )
        )
        await db.delete(cart_item)

    await create_fraud_flag(order, db)
    await db.commit()
    await db.refresh(order)
    return CheckoutResponse(
        **OrderResponse.model_validate(order).model_dump(),
        bank_details=(
            {
                "bank_name": settings.BANK_NAME,
                "account_title": settings.BANK_ACCOUNT_TITLE,
                "account_number": settings.BANK_ACCOUNT_NUMBER,
                "iban": settings.BANK_IBAN,
            }
            if is_bank_transfer
            else None
        ),
    )


@router.get("", response_model=list[OrderResponse])
async def list_orders(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> list[Order]:
    result = await db.scalars(select(Order).where(Order.user_id == user.id).order_by(Order.created_at.desc()))
    return list(result.all())


@router.post("/{order_id}/pay", response_model=OrderResponse)
async def pay_order(
    order_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Order:
    order = await db.scalar(select(Order).where(Order.id == order_id, Order.user_id == user.id))
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.payment_status == "paid":
        raise HTTPException(status_code=409, detail="Order is already paid")
    if order.status in {"cancelled", "refunded", "under_review"}:
        raise HTTPException(status_code=409, detail="This order cannot be paid")

    order.payment_status = "paid"
    if order.status == "awaiting_payment":
        order.status = "confirmed"
    await db.commit()
    await db.refresh(order)
    return order


@router.post("/{order_id}/return", response_model=OrderResponse)
async def request_return(
    order_id: int,
    payload: ReturnRequest | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Order:
    order = await db.scalar(select(Order).where(Order.id == order_id, Order.user_id == user.id))
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    refund_state = run_refund_agent(order, payload.reason if payload else "Customer requested a refund")
    db.add(
        AgentAuditLog(
            agent_name="refund_agent",
            thread_id=f"refund-order-{order.id}",
            user_id=user.id,
            order_id=order.id,
            status="pending_review",
            input_state=refund_state,
            output_state=refund_state,
        )
    )
    order.status = "under_review"
    order.bank_notes = refund_state["admin_note"]
    await db.commit()
    await db.refresh(order)
    return order


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(order_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> Order:
    order = await db.scalar(select(Order).where(Order.id == order_id, Order.user_id == user.id))
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return order
