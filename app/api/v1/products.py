from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.category import Category
from app.models.product import Product
from app.schemas.product import CategoryResponse, ProductResponse

router = APIRouter(prefix="/products", tags=["products"])


@router.get("/categories", response_model=list[CategoryResponse])
async def list_categories(db: AsyncSession = Depends(get_db)) -> list[Category]:
    result = await db.scalars(select(Category).where(Category.is_active.is_(True)).order_by(Category.name))
    return list(result.all())


@router.get("", response_model=list[ProductResponse])
async def list_products(
    category: str | None = None,
    search: str | None = Query(default=None, min_length=1),
    min_price: float | None = Query(default=None, ge=0),
    max_price: float | None = Query(default=None, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> list[Product]:
    statement = select(Product).options(selectinload(Product.category)).where(Product.is_active.is_(True))
    if category:
        statement = statement.join(Product.category).where(Category.slug == category)
    if search:
        statement = statement.where(Product.name.ilike(f"%{search}%"))
    if min_price is not None:
        statement = statement.where(Product.price >= min_price)
    if max_price is not None:
        statement = statement.where(Product.price <= max_price)
    result = await db.scalars(statement.order_by(Product.created_at.desc()).offset(offset).limit(limit))
    return list(result.all())


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(product_id: int, db: AsyncSession = Depends(get_db)) -> Product:
    product = await db.scalar(
        select(Product).options(selectinload(Product.category)).where(Product.id == product_id, Product.is_active.is_(True))
    )
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product
