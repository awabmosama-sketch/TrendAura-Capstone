from typing import TypedDict


class FraudState(TypedDict):
    order_id: int
    ip_address: str
    payment_method: str
    fraud_score: int
    flags: list[str]
    verdict: str


class DiscoveryState(TypedDict):
    query: str
    user_id: int | None
    parsed: dict
    recommendations: list[dict]


class RefundState(TypedDict):
    user_id: int
    order_id: int
    user_message: str
    intent: str
    amount: float
    policy_ok: bool
    decision: str
    admin_note: str | None


class PricingState(TypedDict):
    product_id: int
    product_name: str
    current_price: float
    attempts: int
    competitor_price: float | None
    source_url: str | None
    confidence: float
    suggestion: dict | None


class OnboardingState(TypedDict):
    image_path: str
    product_name: str
    vision_data: dict
    description: str
    seo_tags: list[str]
    category: str
    validation_ok: bool
    iterations: int
    validation_feedback: str
