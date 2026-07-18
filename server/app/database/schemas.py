"""
app/database/schemas.py — Pydantic schemas (v2) matching the updated DB schema definitions.
"""
from datetime import datetime, date
from decimal import Decimal
from typing import Any, List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ─── Auth/User Schemas ────────────────────────────────────────────────────────
class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    phone: Optional[str] = None


class UserRegister(UserBase):
    password: str = Field(min_length=6)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(UserBase):
    id: UUID
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


# ─── Category Schemas ─────────────────────────────────────────────────────────
class CategoryBase(BaseModel):
    name: str
    slug: str
    icon: Optional[str] = None
    image_url: Optional[str] = None
    product_count: int = 0


class CategoryCreate(CategoryBase):
    pass


class CategoryResponse(CategoryBase):
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─── Product Schemas ──────────────────────────────────────────────────────────
class ProductBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: Decimal
    original_price: Optional[Decimal] = None
    category: str
    brand: Optional[str] = None
    image_url: Optional[str] = None
    images: Optional[List[str]] = None
    stock_quantity: int = 0
    is_featured: bool = False
    is_active: bool = True
    rating: float = 0.0
    review_count: int = 0
    tags: Optional[List[str]] = None


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[Decimal] = None
    original_price: Optional[Decimal] = None
    category: Optional[str] = None
    brand: Optional[str] = None
    image_url: Optional[str] = None
    images: Optional[List[str]] = None
    stock_quantity: Optional[int] = None
    is_featured: Optional[bool] = None
    is_active: Optional[bool] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    tags: Optional[List[str]] = None


class ProductResponse(ProductBase):
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─── Product Review Schemas ───────────────────────────────────────────────────
class ProductReviewCreate(BaseModel):
    reviewer_name: str = "Customer"
    rating: int = Field(ge=1, le=5)
    review_text: str


class ProductReviewResponse(BaseModel):
    id: UUID
    product_id: UUID
    reviewer_name: str
    rating: int
    review_text: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─── Order Schemas ────────────────────────────────────────────────────────────
class OrderCreate(BaseModel):
    customer_name: Optional[str] = None
    customer_email: Optional[EmailStr] = None
    customer_phone: Optional[str] = None
    items: List[dict]  # Array of product/quantity dicts as stored inSupabase JSONB
    total_amount: Decimal
    payment_method: Optional[str] = None
    shipping_address: Optional[dict] = None
    estimated_delivery: Optional[date] = None


class OrderUpdate(BaseModel):
    status: Optional[str] = None
    payment_status: Optional[str] = None
    tracking_number: Optional[str] = None
    estimated_delivery: Optional[date] = None


class OrderResponse(BaseModel):
    id: UUID
    order_number: str
    customer_name: Optional[str] = None
    customer_email: Optional[EmailStr] = None
    customer_phone: Optional[str] = None
    items: List[dict]
    total_amount: Decimal
    status: str
    payment_method: Optional[str] = None
    payment_status: str
    shipping_address: Optional[dict] = None
    tracking_number: Optional[str] = None
    estimated_delivery: Optional[date] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OrderTrackResponse(BaseModel):
    id: UUID
    order_number: str
    status: str
    tracking_number: Optional[str] = None
    estimated_delivery: Optional[date] = None


# ─── Return Schemas ───────────────────────────────────────────────────────────
class ReturnCreate(BaseModel):
    order_id: UUID
    reason: str


class ReturnUpdate(BaseModel):
    status: Optional[str] = None
    refund_amount: Optional[Decimal] = None


class ReturnResponse(BaseModel):
    id: UUID
    return_number: str
    order_id: UUID
    reason: str
    status: str
    refund_amount: Optional[Decimal] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─── FAQ Schemas ──────────────────────────────────────────────────────────────
class FAQBase(BaseModel):
    question: str
    answer: str
    category: str


class FAQCreate(FAQBase):
    pass


class FAQResponse(FAQBase):
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─── Chat Schemas ─────────────────────────────────────────────────────────────
class ChatMessageBase(BaseModel):
    role: str
    content: str
    timestamp: Optional[datetime] = None


class ChatSessionResponse(BaseModel):
    id: UUID
    session_id: str
    messages: List[dict] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatStreamRequest(BaseModel):
    session_key: str
    message: str


# ─── Standard Response Wrapper ────────────────────────────────────────────────
class StandardResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None
    errors: Optional[Any] = None
