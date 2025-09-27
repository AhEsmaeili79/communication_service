from pydantic import BaseModel, Field, field_validator, EmailStr
from typing import Optional
from datetime import datetime


class EmailRequest(BaseModel):
    to: EmailStr = Field(..., description="Recipient email address")
    subject: Optional[str] = Field(None, description="Email subject (optional, defaults to welcome message)")
    body: Optional[str] = Field(None, description="Email body content (optional, defaults to welcome message)")

    model_config = {
        "json_schema_extra": {
            "example": {
                "to": "user@example.com",
                "subject": "Your OTP Code",
                "body": "Your OTP code is: 123456"
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
