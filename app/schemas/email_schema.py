from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class EmailRequest(BaseModel):
    to: EmailStr

class EmailResponse(BaseModel):
    message_id: str
    status: str
    sent_at: datetime
    to: EmailStr
    subject: str

    class Config:
        from_attributes = True


class EmailStatus(BaseModel):
    message_id: str
    status: str
    delivered_at: Optional[datetime] = None
    error_message: Optional[str] = None
