from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID
from datetime import datetime

class CategoryBase(BaseModel):
    name: str = Field(..., max_length=100)

class CategoryCreate(CategoryBase):
    pass

class CategoryOut(CategoryBase):
    id: UUID
    slug: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
