from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime


class CategoryBase(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    is_active: bool = True


class CategoryCreate(CategoryBase):
    pass


class CategoryResponse(CategoryBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime


class ProductBase(BaseModel):
    name: str
    slug: str
    sku: str
    description: str
    price: float
    compare_at_price: Optional[float] = None
    stock_quantity: int = 0
    category_id: int
    is_active: bool = True
    is_featured: bool = False
    image_url: str
    images: Optional[List[str]] = []


class ProductCreate(ProductBase):
    vendor_id: Optional[int] = None


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    sku: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    compare_at_price: Optional[float] = None
    stock_quantity: Optional[int] = None
    category_id: Optional[int] = None
    is_active: Optional[bool] = None
    is_featured: Optional[bool] = None
    image_url: Optional[str] = None
    images: Optional[List[str]] = None


class ProductResponse(ProductBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    vendor_id: Optional[int] = None
    created_at: datetime
    category: Optional[CategoryResponse] = None
