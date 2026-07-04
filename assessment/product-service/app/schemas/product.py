from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from uuid import UUID
from datetime import datetime

class ProductBase(BaseModel):
    name: str = Field(..., max_length=200)
    description: Optional[str] = None
    price: float = Field(..., ge=0)
    stock_quantity: int = Field(0, ge=0)
    category_id: UUID
    is_active: bool = True

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    price: Optional[float] = Field(None, ge=0)
    stock_quantity: Optional[int] = Field(None, ge=0)
    category_id: Optional[UUID] = None
    is_active: Optional[bool] = None

class ProductStockUpdate(BaseModel):
    delta: int

class ProductOut(ProductBase):
    id: UUID
    slug: str
    created_by: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ProductListOut(BaseModel):
    total_count: int
    items: list[ProductOut]
