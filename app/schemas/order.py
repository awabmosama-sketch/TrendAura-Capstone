from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AddressInput(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    phone: str = Field(min_length=5, max_length=50)
    street_address: str = Field(min_length=1, max_length=255)
    landmark: str | None = Field(default=None, max_length=255)
    city: str = Field(min_length=1, max_length=100)
    postal_code: str = Field(min_length=1, max_length=20)
    country: str = Field(default="Pakistan", max_length=100)


class CheckoutRequest(BaseModel):
    payment_method: Literal["bank_transfer", "cod"]
    shipping_address: AddressInput
    promo_code: str | None = Field(default=None, max_length=50)


class ReturnRequest(BaseModel):
    reason: str = Field(default="Customer requested a refund", min_length=1, max_length=500)


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_number: str
    total_amount: Decimal
    discount_amount: Decimal
    final_amount: Decimal
    status: str
    payment_method: str
    payment_status: str
    payment_reference_code: str | None
    created_at: datetime


class CheckoutResponse(OrderResponse):
    bank_details: dict[str, str] | None = None
