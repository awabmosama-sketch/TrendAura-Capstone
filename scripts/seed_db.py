import asyncio
from decimal import Decimal

from sqlalchemy import select

from app.core.database import AsyncSessionLocal, engine
from app.core.security import get_password_hash
from app.models import Base, Category, Product, User

CATEGORIES = [
    ("Outerwear & Jackets", "outerwear-jackets"),
    ("Footwear & Shoes", "footwear-shoes"),
    ("Minimalist Apparel", "minimalist-apparel"),
    ("Everyday Accessories", "everyday-accessories"),
    ("Unisex Fragrance", "unisex-fragrance"),
]

PRODUCTS = [
    ("Leather Biker Jacket", "outerwear-jackets", "A clean-cut leather jacket for year-round layering.", "https://images.unsplash.com/photo-1551028719-00167b16eac5", Decimal("8900"), "JKT-001"),
    ("Minimalist Runner Sneakers", "footwear-shoes", "Lightweight neutral runners built for everyday movement.", "https://images.unsplash.com/photo-1542291026-7eec264c27ff", Decimal("4800"), "SHO-001"),
    ("Oversized Cotton Hoodie", "minimalist-apparel", "Heavyweight cotton with a relaxed unisex silhouette.", "https://images.unsplash.com/photo-1551488831-00ddcb6c6bd3", Decimal("3200"), "APP-001"),
    ("Smoked Cedar Eau de Parfum", "unisex-fragrance", "Dry cedar, amber, and citrus in a balanced daily scent.", "https://images.unsplash.com/photo-1541643600914-78b084683601", Decimal("5200"), "FRG-001"),
]


async def seed() -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        categories: dict[str, Category] = {}
        for name, slug in CATEGORIES:
            category = await session.scalar(select(Category).where(Category.slug == slug))
            if category is None:
                category = Category(name=name, slug=slug, is_active=True)
                session.add(category)
                await session.flush()
            categories[slug] = category

        for name, category_slug, description, image_url, price, sku in PRODUCTS:
            exists = await session.scalar(select(Product).where(Product.sku == sku))
            if exists is None:
                session.add(Product(
                    name=name,
                    slug=sku.lower(),
                    sku=sku,
                    description=description,
                    price=price,
                    stock_quantity=20,
                    category_id=categories[category_slug].id,
                    image_url=image_url,
                    is_featured=True,
                ))

        defaults = [
            ("admin@trendaura.pk", "TrendAura Admin", "admin"),
            ("vendor@trendaura.pk", "TrendAura Vendor", "vendor"),
            ("customer@trendaura.pk", "TrendAura Customer", "customer"),
        ]
        for email, full_name, role in defaults:
            exists = await session.scalar(select(User).where(User.email == email))
            if exists is None:
                session.add(User(email=email, full_name=full_name, role=role, is_active=True, is_verified=True, hashed_password=get_password_hash("change-me")))

        await session.commit()


if __name__ == "__main__":
    asyncio.run(seed())
