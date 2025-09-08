from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
import re


class SMSRequest(BaseModel):
    to: str = Field(..., min_length=10, max_length=20, description="Phone number in international format")
    text: str = Field(..., min_length=1, max_length=1600, description="SMS text content")
    from_number: Optional[str] = Field(None, min_length=10, max_length=20, description="Sender phone number")

    @validator('to')
    def validate_to_phone(cls, v):
        # Phone number validation - supports international and local formats
        # Allows: +98xxxxxxxxxx, 09xxxxxxxxx, 0098xxxxxxxxxx
        clean_phone = re.sub(r'[\s\-\(\)]', '', v)
        
        # Patterns for different phone number formats
        patterns = [
            r'^\+98[0-9]{10}$',      # +98xxxxxxxxxx (Iran international)
            r'^0098[0-9]{10}$',      # 0098xxxxxxxxxx (Iran international with 00)
            r'^09[0-9]{9}$',         # 09xxxxxxxxx (Iran local)
            r'^\+?[1-9]\d{1,14}$'    # General international format
        ]
        
        if not any(re.match(pattern, clean_phone) for pattern in patterns):
            raise ValueError('Invalid phone number format. Supported formats: +98xxxxxxxxxx, 09xxxxxxxxx, 0098xxxxxxxxxx')
        return clean_phone

    @validator('from_number')
    def validate_from_phone(cls, v):
        if v is not None:
            clean_phone = re.sub(r'[\s\-\(\)]', '', v)
            
            # Patterns for different phone number formats
            patterns = [
                r'^\+98[0-9]{10}$',      # +98xxxxxxxxxx (Iran international)
                r'^0098[0-9]{10}$',      # 0098xxxxxxxxxx (Iran international with 00)
                r'^09[0-9]{9}$',         # 09xxxxxxxxx (Iran local)
                r'^5000[0-9]{10}$',     # 5000xxxxxxxxxx (Iran SMS sender)
                r'^\+?[1-9]\d{1,14}$'    # General international format
            ]
            
            if not any(re.match(pattern, clean_phone) for pattern in patterns):
                raise ValueError('Invalid sender phone number format. Supported formats: +98xxxxxxxxxx, 09xxxxxxxxx, 5000xxxxxxxxxx')
            return clean_phone
        return v

    @validator('text')
    def validate_text(cls, v):
        if not v or not v.strip():
            raise ValueError('SMS text cannot be empty')
        return v.strip()

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
    recId: Optional[int] = None
    status: str
    sent_at: datetime
    to: str
    text: str
    from_number: str

    model_config = {
        "from_attributes": True
    }


class SMSApiResponse(BaseModel):
    recId: Optional[int] = None
    status: str

    model_config = {
        "from_attributes": True
    }
