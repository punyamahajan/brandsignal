from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class BrandContextRequest(BaseModel):
    brand_name: Optional[str] = None
    industry: Optional[str] = None
    category: Optional[str] = None
    geography: Optional[str] = None
    business_model: Optional[str] = None
    target_customer: Optional[str] = None
    price_positioning: Optional[str] = None
    customer_segment: Optional[str] = None
    is_demo_vertical: Optional[bool] = False
    demo_brand_id: Optional[str] = None
    competitors: Optional[List[str]] = Field(default_factory=list)

class BrandContextResponse(BaseModel):
    brand_name: Optional[str] = None
    industry: Optional[str] = None
    category: Optional[str] = None
    geography: Optional[str] = None
    business_model: Optional[str] = None
    target_customer: Optional[str] = None
    price_positioning: Optional[str] = None
    customer_segment: Optional[str] = None
    is_demo_vertical: bool = False
    demo_brand_id: Optional[str] = None
    competitors: List[str] = Field(default_factory=list)
    status: str = "INITIAL"
    summary: str = ""
    is_established: bool = False

