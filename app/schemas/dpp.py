from pydantic import BaseModel, Field, constr
from typing import Optional

class DPPBase(BaseModel):
    product_id: constr(min_length=3, max_length=100)
    manufacturer: str
    serial_number: Optional[str]
    model_number: Optional[str]
    production_date: Optional[str]
    material_composition: Optional[str]
    lifecycle_status: Optional[str]
    recycling_instructions: Optional[str]


class DPPCreate(DPPBase):
    pass

class DPPUpdate(DPPBase):
    pass

class DPPResponse(DPPBase):
    id: int

    class Config:
        from_attributes = True
