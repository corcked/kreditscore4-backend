from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, List

class UserBase(BaseModel):
    telegram_id: int
    phone_number: Optional[str] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    loan_amount: Optional[float] = None
    loan_term: Optional[int] = None
    loan_purpose: Optional[str] = None
    monthly_income: Optional[float] = None

class UserCreate(UserBase):
    pass

class UserUpdate(BaseModel):
    phone_number: Optional[str] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    loan_amount: Optional[float] = None
    loan_term: Optional[int] = None
    loan_purpose: Optional[str] = None
    monthly_income: Optional[float] = None

class User(UserBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

class AuthSessionBase(BaseModel):
    user_agent: Optional[str] = None
    device_info: Optional[str] = None
    ip_address: Optional[str] = None

class AuthSessionCreate(AuthSessionBase):
    user_id: int
    token: str
    expires_at: datetime

class AuthSession(AuthSessionBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    token: str
    user_id: int
    is_active: bool
    created_at: datetime
    expires_at: datetime
    user: User

class AuthTokenRequest(BaseModel):
    user_agent: Optional[str] = None
    device_info: Optional[str] = None
    loan_amount: Optional[float] = None
    loan_term: Optional[int] = None
    loan_purpose: Optional[str] = None
    monthly_income: Optional[float] = None

class AuthTokenResponse(BaseModel):
    auth_token: str
    telegram_url: str

class VerifyTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: User
    session: AuthSession
    device_info: dict

# Bot API schemas
class BotAuthInitRequest(BaseModel):
    loan_amount: Optional[float] = None
    loan_term: Optional[int] = None
    loan_purpose: Optional[str] = None
    monthly_income: Optional[float] = None

class BotAuthInitResponse(BaseModel):
    auth_token: str
    telegram_url: str

class BotAuthCompleteRequest(BaseModel):
    auth_token: str
    telegram_id: int
    phone: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None

class BotAuthCompleteResponse(BaseModel):
    success: bool
    frontend_return_url: str
    user_id: int

class BotUserResponse(BaseModel):
    id: int
    telegram_id: int
    phone_number: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
    loan_amount: Optional[float] = None
    loan_term: Optional[int] = None
    loan_purpose: Optional[str] = None
    monthly_income: Optional[float] = None
    created_at: datetime
    updated_at: Optional[datetime] = None 