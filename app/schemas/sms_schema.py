from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class SMSRequest(BaseModel):
    to: str
    text: str
    from_number: Optional[str] = None

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
