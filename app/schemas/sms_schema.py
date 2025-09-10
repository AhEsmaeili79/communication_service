from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime

from app.utils.validators import PhoneValidator, validate_sms_text


class SMSRequest(BaseModel):
    to: str = Field(..., min_length=10, max_length=20, description="Phone number in international format")
    text: str = Field(..., min_length=1, max_length=1600, description="SMS text content")
    from_number: Optional[str] = Field(None, min_length=10, max_length=20, description="Sender phone number")

    @field_validator('to')
    @classmethod
    def validate_to_phone(cls, v):
        return PhoneValidator.validate_phone_number(v, "recipient phone number")

    @field_validator('from_number')
    @classmethod
    def validate_from_phone(cls, v):
        if v is not None:
            return PhoneValidator.validate_phone_number(v, "sender phone number")
        return v

    @field_validator('text')
    @classmethod
    def validate_text(cls, v):
        return validate_sms_text(v)

    model_config = {
        "json_schema_extra": {
            "example": {
                "to": "09199078934",
                "text": "test sms",
                "from_number": "50002710078934"
            }
        }
    }




class SMSResponse(BaseModel):
    to: str
    status: str

    model_config = {
        "from_attributes": True
    }


class SMSApiResponse(BaseModel):
    recId: Optional[int] = None
    status: str

    model_config = {
        "from_attributes": True
    }
