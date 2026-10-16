import asyncio

import pytest
from fastapi.testclient import TestClient

from app.core.database import AsyncSessionLocal, engine
from app.core.security import get_password_hash
from app.main import app
from app.models import Base
from app.models.category import Category
from app.models.product import Product
from app.models.user import User


CUSTOMER = {
    "email": "customer@example.com",
    "full_name": "Test Customer",
    "password": "StrongPassword123!",
}
ADMIN = {
    "email": "admin@example.com",
    "full_name": "Test Admin",
    "password": "AdminPassword123!",
}
ADDRESS = {
    "first_name": "Test",
    "last_name": "Customer",
    "phone": "+923001234567",
    "street_address": "123 Test Street",
    "city": "Karachi",
    "postal_code": "74000",
}


async def reset_database() -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)


async def seed_database() -> None:
    async with AsyncSessionLocal() as session:
        category = Category(name="Test Fashion", slug="test-fashion")
        admin = User(
            email=ADMIN["email"],
            full_name=ADMIN["full_name"],
            hashed_password=get_password_hash(ADMIN["password"]),
            role="admin",
            is_verified=True,
        )
        session.add_all([category, admin])
        await session.flush()
        session.add(
            Product(
                name="Test T-Shirt",
                slug="test-t-shirt",
                sku="TEST-TSHIRT-001",
                description="A product used by the API tests.",
                price=1500,
                stock_quantity=10,
                category_id=category.id,
                image_url="https://example.com/test-t-shirt.jpg",
                images=[],
            )
        )
        await session.commit()


@pytest.fixture()
def client() -> TestClient:
    asyncio.run(reset_database())
    with TestClient(app) as test_client:
        asyncio.run(seed_database())
        yield test_client


def login(client: TestClient, credentials: dict[str, str]) -> str:
    response = client.post("/api/v1/auth/login", json=credentials)
    assert response.status_code == 200
    return response.json()["access_token"]


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def login_after_register(client: TestClient, email: str = CUSTOMER["email"]) -> str:
    credentials = {**CUSTOMER, "email": email}
    registration = client.post("/api/v1/auth/register", json=credentials)
    assert registration.status_code == 201
    return login(client, credentials)


def test_public_and_auth_apis(client: TestClient) -> None:
    health = client.get("/api/v1/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    categories = client.get("/api/v1/products/categories")
    assert categories.status_code == 200
    assert categories.json()[0]["slug"] == "test-fashion"

    products = client.get("/api/v1/products", params={"search": "T-Shirt"})
    assert products.status_code == 200
    product = products.json()[0]
    assert product["name"] == "Test T-Shirt"

    product_detail = client.get(f"/api/v1/products/{product['id']}")
    assert product_detail.status_code == 200
    assert product_detail.json()["id"] == product["id"]

    registration = client.post("/api/v1/auth/register", json=CUSTOMER)
    assert registration.status_code == 201
    assert registration.json()["email"] == CUSTOMER["email"]

    duplicate = client.post("/api/v1/auth/register", json=CUSTOMER)
    assert duplicate.status_code == 409

    special_admin = client.post(
        "/api/v1/auth/register",
        json={"email": "admin@trendaura.pk", "full_name": "Refund Team", "password": "StrongPassword123!"},
    )
    assert special_admin.status_code == 201
    assert special_admin.json()["role"] == "admin"

    token = login(client, CUSTOMER)
    me = client.get("/api/v1/auth/me", headers=auth_headers(token))
    assert me.status_code == 200
    assert me.json()["email"] == CUSTOMER["email"]
    assert client.get("/api/v1/auth/me").status_code == 401


def test_cart_and_customer_order_apis(client: TestClient) -> None:
    customer_token = login_after_register(client)
    headers = auth_headers(customer_token)

    empty_cart = client.get("/api/v1/cart", headers=headers)
    assert empty_cart.status_code == 200
    assert empty_cart.json()["items"] == []

    product_id = client.get("/api/v1/products").json()[0]["id"]
    add_item = client.post(
        "/api/v1/cart/items",
        json={"product_id": product_id, "quantity": 2},
        headers=headers,
    )
    assert add_item.status_code == 201
    item = add_item.json()["items"][0]
    assert item["quantity"] == 2
    assert add_item.json()["subtotal"] == "3000.00"

    update_item = client.patch(
        f"/api/v1/cart/items/{item['id']}",
        json={"quantity": 1},
        headers=headers,
    )
    assert update_item.status_code == 200
    assert update_item.json()["items"][0]["quantity"] == 1

    empty_checkout = client.post(
        "/api/v1/orders/checkout",
        json={"payment_method": "cod", "shipping_address": ADDRESS},
        headers=auth_headers(login_after_register(client, "second@example.com")),
    )
    assert empty_checkout.status_code == 400

    checkout = client.post(
        "/api/v1/orders/checkout",
        json={"payment_method": "cod", "shipping_address": ADDRESS},
        headers=headers,
    )
    assert checkout.status_code == 201
    order = checkout.json()
    assert order["status"] == "confirmed"
    assert order["payment_status"] == "pending_on_delivery"

    payment = client.post(f"/api/v1/orders/{order['id']}/pay", headers=headers)
    assert payment.status_code == 200
    assert payment.json()["payment_status"] == "paid"

    orders = client.get("/api/v1/orders", headers=headers)
    assert orders.status_code == 200
    assert orders.json()[0]["id"] == order["id"]

    order_detail = client.get(f"/api/v1/orders/{order['id']}", headers=headers)
    assert order_detail.status_code == 200
    assert order_detail.json()["order_number"] == order["order_number"]

    return_request = client.post(f"/api/v1/orders/{order['id']}/return", headers=headers)
    assert return_request.status_code == 200
    assert return_request.json()["status"] == "under_review"

    remove_item = client.delete(
        f"/api/v1/cart/items/{item['id']}",
        headers=headers,
    )
    assert remove_item.status_code == 404


def test_bank_transfer_and_admin_apis(client: TestClient) -> None:
    customer_token = login_after_register(client, "bank-customer@example.com")
    customer_headers = auth_headers(customer_token)
    product_id = client.get("/api/v1/products").json()[0]["id"]
    client.post(
        "/api/v1/cart/items",
        json={"product_id": product_id, "quantity": 1},
        headers=customer_headers,
    )

    checkout = client.post(
        "/api/v1/orders/checkout",
        json={"payment_method": "bank_transfer", "shipping_address": ADDRESS},
        headers=customer_headers,
    )
    assert checkout.status_code == 201
    order = checkout.json()
    assert order["status"] == "awaiting_payment"
    assert order["payment_status"] == "pending_verification"
    assert order["bank_details"]["bank_name"]

    assert client.get("/api/v1/admin/orders", headers=customer_headers).status_code == 403

    admin_token = login(client, ADMIN)
    admin_headers = auth_headers(admin_token)
    admin_orders = client.get("/api/v1/admin/orders", headers=admin_headers)
    assert admin_orders.status_code == 200
    assert admin_orders.json()[0]["id"] == order["id"]

    verification = client.post(
        f"/api/v1/admin/orders/{order['id']}/verify-payment",
        headers=admin_headers,
    )
    assert verification.status_code == 200
    assert verification.json()["status"] == "confirmed"
    assert verification.json()["payment_status"] == "paid"

    large_order_item = client.post(
        "/api/v1/cart/items",
        json={"product_id": product_id, "quantity": 4},
        headers=customer_headers,
    )
    assert large_order_item.status_code == 201
    large_checkout = client.post(
        "/api/v1/orders/checkout",
        json={"payment_method": "cod", "shipping_address": ADDRESS},
        headers=customer_headers,
    )
    assert large_checkout.status_code == 201
    large_order = large_checkout.json()
    assert client.post(f"/api/v1/orders/{large_order['id']}/pay", headers=customer_headers).status_code == 200

    refund_request = client.post(
        f"/api/v1/orders/{large_order['id']}/return",
        json={"reason": "The items arrived damaged and need a full review."},
        headers=customer_headers,
    )
    assert refund_request.status_code == 200
    assert refund_request.json()["status"] == "under_review"

    pending_refunds = client.get("/api/v1/admin/refunds", headers=admin_headers)
    assert pending_refunds.status_code == 200
    refund_case = next(item for item in pending_refunds.json() if item["order_id"] == large_order["id"])
    decision = client.post(f"/api/v1/admin/refunds/{refund_case['id']}/approve", headers=admin_headers)
    assert decision.status_code == 200
    assert decision.json()["order_status"] == "refunded"


def test_agent_and_dashboard_apis(client: TestClient) -> None:
    customer_token = login_after_register(client, "agent-customer@example.com")
    admin_token = login(client, ADMIN)
    customer_headers = auth_headers(customer_token)
    admin_headers = auth_headers(admin_token)

    recommendations = client.get("/api/v1/agents/recommendations", params={"q": "shirt under 5000"}, headers=customer_headers)
    assert recommendations.status_code == 200
    assert recommendations.json()["recommendations"]

    categories = client.get("/api/v1/products/categories")
    onboarding = client.post(
        "/api/v1/agents/onboarding",
        data={"name": "Utility Overshirt", "category_id": categories.json()[0]["id"], "price": "2400", "stock_quantity": "8", "sku": "AGENT-001"},
        headers=admin_headers,
    )
    assert onboarding.status_code == 201
    assert onboarding.json()["seo_tags"]

    audit = client.post("/api/v1/admin/pricing-audit", headers=admin_headers)
    assert audit.status_code == 200
    assert client.get("/api/v1/admin/pricing-suggestions", headers=admin_headers).status_code == 200
    assert client.get("/api/v1/admin/fraud/flags", headers=admin_headers).status_code == 200
    assert client.get("/api/v1/admin/stats", headers=admin_headers).status_code == 200