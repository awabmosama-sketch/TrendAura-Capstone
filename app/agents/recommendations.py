import re
from decimal import Decimal

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.order import OrderItem
from app.models.product import Product


def parse_query(query: str) -> tuple[list[str], Decimal | None]:
    normalized = query.casefold()
    max_price = None
    price_match = re.search(r"(?:under|below|less than|up to)\s*(\d+(?:\.\d+)?)", normalized)
    if price_match:
        max_price = Decimal(price_match.group(1))
    terms = [term for term in re.findall(r"[a-z0-9]+", normalized) if term not in {"under", "below", "less", "than", "up", "to", "for", "and"}]
    return terms, max_price


async def discover_products(query: str, db: AsyncSession, user_id: int | None = None) -> list[dict]:
    terms, max_price = parse_query(query)
    statement = select(Product).options(selectinload(Product.category)).where(Product.is_active.is_(True))
    if max_price is not None:
        statement = statement.where(Product.price <= max_price)
    if terms:
        matches = [or_(Product.name.ilike(f"%{term}%"), Product.description.ilike(f"%{term}%")) for term in terms]
        statement = statement.where(or_(*matches))
    products = list((await db.scalars(statement.order_by(Product.is_featured.desc(), Product.created_at.desc()).limit(30))).all())

    history_names: set[str] = set()
    if user_id:
        history = await db.scalars(select(OrderItem.product_name).join(OrderItem.order).where(OrderItem.order.has(user_id=user_id)).limit(10))
        history_names = {name.casefold() for name in history.all()}

    results = []
    for product in products:
        relevance = sum(term in f"{product.name} {product.description}".casefold() for term in terms)
        history_affinity = int(product.name.casefold() in history_names)
        score = relevance * 0.6 + history_affinity * 0.3 + int(product.is_featured) * 0.1
        results.append({"product": product, "score": score, "matched_terms": terms})
    results.sort(key=lambda item: item["score"], reverse=True)
    return results
