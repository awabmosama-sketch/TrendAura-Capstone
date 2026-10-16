from decimal import Decimal

from app.models.product import Product


def audit_product(product: Product) -> dict:
    price = Decimal(product.price)
    inventory_pressure = product.stock_quantity <= 5
    estimated_competitor = (price * Decimal("0.95") if inventory_pressure else price * Decimal("1.08")).quantize(Decimal("0.01"))
    action = "raise" if estimated_competitor > price else "lower" if estimated_competitor < price else "keep"
    return {
        "product_id": product.id,
        "product_name": product.name,
        "current_price": float(price),
        "suggested_price": float(estimated_competitor),
        "competitor_price": float(estimated_competitor),
        "action": action,
        "confidence": 0.65,
        "reason": "Deterministic local audit based on inventory pressure; replace with Tavily results when configured.",
        "source_url": None,
    }
