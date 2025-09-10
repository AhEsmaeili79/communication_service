from pydantic import BaseModel, Field, field_validator, EmailStr
from typing import Optional
from datetime import datetime


class EmailRequest(BaseModel):
    to: EmailStr = Field(..., description="Recipient email address")

    model_config = {
        "json_schema_extra": {
            "example": {
                "to": "user@example.com"
            }
        }
    }


class EmailResponse(BaseModel):
    to: str
    status: str

    model_config = {
        "from_attributes": True
    }


class EmailApiResponse(BaseModel):
    message_id: Optional[str] = None
    status: str

    model_config = {
        "from_attributes": True
    }
