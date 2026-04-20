from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from models import MovementType, OrderStatus, UserRole


# ========= Auth =========
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    name: str = Field(min_length=1, max_length=200)
    phone: str | None = None
    address: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    email: EmailStr
    role: UserRole
    is_active: bool


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=16, max_length=256)
    new_password: str = Field(min_length=6, max_length=128)


class SimpleMessage(BaseModel):
    message: str


# ========= Clients =========
class ClientBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    phone: str | None = None
    address: str | None = None


class ClientCreate(ClientBase):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class ClientUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    address: str | None = None


class ClientOut(ClientBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    user_id: UUID
    email: EmailStr | None = None
    active: bool
    created_at: datetime


# ========= Products =========
class ProductBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    price: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    stock: int = Field(ge=0, default=0)
    category: str | None = None
    image_url: str | None = None


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    price: Decimal | None = Field(default=None, ge=0)
    stock: int | None = Field(default=None, ge=0)
    category: str | None = None
    image_url: str | None = None
    active: bool | None = None


class ProductOut(ProductBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    active: bool
    created_at: datetime


# ========= Orders =========
class OrderItemIn(BaseModel):
    product_id: UUID
    quantity: int = Field(gt=0)


class OrderCreate(BaseModel):
    items: list[OrderItemIn] = Field(min_length=1)
    payment_method: str | None = None
    notes: str | None = None


class OrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    product_id: UUID
    quantity: int
    unit_price: Decimal
    product_name: str | None = None


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    client_id: UUID
    total: Decimal
    status: OrderStatus
    payment_method: str | None
    notes: str | None
    created_at: datetime
    items: list[OrderItemOut] = []
    client_name: str | None = None


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


# ========= Inventory =========
class MovementCreate(BaseModel):
    product_id: UUID
    type: MovementType
    quantity: int = Field(gt=0)
    reason: str | None = None


class MovementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    product_id: UUID
    type: MovementType
    quantity: int
    reason: str | None
    user_id: UUID | None
    created_at: datetime
    product_name: str | None = None


# ========= Reports =========
class SalesReportItem(BaseModel):
    date: date
    total: Decimal
    count: int


class TopProductItem(BaseModel):
    product_id: UUID
    name: str
    quantity: int
    revenue: Decimal


TokenResponse.model_rebuild()
