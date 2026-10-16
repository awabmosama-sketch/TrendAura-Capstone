from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.cart import Cart, CartItem
from app.models.product import Product
from app.models.user import User
from app.schemas.cart import CartItemCreate, CartItemResponse, CartItemUpdate, CartResponse

router = APIRouter(prefix="/cart", tags=["cart"])


async def get_or_create_cart(user: User, db: AsyncSession) -> Cart:
    cart = await db.scalar(
        select(Cart).options(selectinload(Cart.items).selectinload(CartItem.product)).where(Cart.user_id == user.id)
    )
    if cart is None:
        cart = Cart(user_id=user.id, items=[])
        db.add(cart)
        await db.commit()
        await db.refresh(cart)
        await db.refresh(cart, attribute_names=["items"])
    return cart


def serialize_cart(cart: Cart) -> CartResponse:
    items = [
        CartItemResponse(
            id=item.id,
            product_id=item.product_id,
            quantity=item.quantity,
            unit_price=Decimal(item.product.price),
            subtotal=Decimal(item.product.price) * item.quantity,
        )
        for item in cart.items
    ]
    return CartResponse(id=cart.id, items=items, subtotal=sum((item.subtotal for item in items), Decimal("0")))


@router.get("", response_model=CartResponse)
async def get_cart(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> CartResponse:
    return serialize_cart(await get_or_create_cart(user, db))


@router.post("/items", response_model=CartResponse, status_code=status.HTTP_201_CREATED)
async def add_to_cart(
    payload: CartItemCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CartResponse:
    cart = await get_or_create_cart(user, db)
    product = await db.get(Product, payload.product_id)
    if product is None or not product.is_active:
        raise HTTPException(status_code=404, detail="Product not found")
    if product.stock_quantity < payload.quantity:
        raise HTTPException(status_code=409, detail="Insufficient stock")

    item = next((existing for existing in cart.items if existing.product_id == product.id), None)
    if item is None:
        cart.items.append(CartItem(product_id=product.id, quantity=payload.quantity, product=product))
    else:
        if item.quantity + payload.quantity > product.stock_quantity:
            raise HTTPException(status_code=409, detail="Insufficient stock")
        item.quantity += payload.quantity
    await db.commit()
    return serialize_cart(await get_or_create_cart(user, db))


@router.patch("/items/{item_id}", response_model=CartResponse)
async def update_cart_item(
    item_id: int,
    payload: CartItemUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CartResponse:
    cart = await get_or_create_cart(user, db)
    item = next((existing for existing in cart.items if existing.id == item_id), None)
    if item is None:
        raise HTTPException(status_code=404, detail="Cart item not found")
    if payload.quantity > item.product.stock_quantity:
        raise HTTPException(status_code=409, detail="Insufficient stock")
    item.quantity = payload.quantity
    await db.commit()
    return serialize_cart(await get_or_create_cart(user, db))


@router.delete("/items/{item_id}", response_model=CartResponse)
async def remove_cart_item(
    item_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CartResponse:
    cart = await get_or_create_cart(user, db)
    item = next((existing for existing in cart.items if existing.id == item_id), None)
    if item is None:
        raise HTTPException(status_code=404, detail="Cart item not found")
    await db.delete(item)
    await db.commit()
    return serialize_cart(await get_or_create_cart(user, db))
