from fastapi import APIRouter, HTTPException, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
import os
from datetime import datetime

from ..database import get_db
from ..models.user import User
from ..models.schemas import (
    BotAuthInitRequest,
    BotAuthInitResponse,
    BotAuthCompleteRequest,
    BotAuthCompleteResponse,
    BotUserResponse
)
from ..services.auth_service import auth_token_service

router = APIRouter(tags=["bot"])

BOT_API_KEY = os.getenv("BOT_API_KEY", "default-bot-api-key-change-in-production")


async def verify_bot_token(x_bot_token: str = Header(...)) -> bool:
    """Verify that the request comes from our bot service"""
    if x_bot_token != BOT_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid bot token")
    return True


@router.post("/auth/init", response_model=BotAuthInitResponse)
async def init_bot_auth(
    request: BotAuthInitRequest,
    _: bool = Depends(verify_bot_token)
):
    """Initialize bot authentication process"""
    loan_data = {
        "loan_amount": request.loan_amount,
        "loan_term": request.loan_term,
        "loan_purpose": request.loan_purpose,
        "monthly_income": request.monthly_income
    }
    
    auth_token = auth_token_service.create_auth_token(loan_data)
    
    bot_username = os.getenv("TELEGRAM_BOT_USERNAME", "kreditscore4_bot")
    telegram_url = f"https://t.me/{bot_username}?start={auth_token}"
    
    return BotAuthInitResponse(
        auth_token=auth_token,
        telegram_url=telegram_url
    )


@router.post("/auth/complete", response_model=BotAuthCompleteResponse)
async def complete_bot_auth(
    request: BotAuthCompleteRequest,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_bot_token)
):
    """Complete bot authentication process"""
    is_valid, error_msg = auth_token_service.verify_auth_token(request.auth_token)
    if not is_valid:
        raise HTTPException(
            status_code=404 if "Invalid" in error_msg else 410,
            detail=error_msg
        )
    
    loan_data = auth_token_service.get_loan_data(request.auth_token) or {}
    
    # Check if user exists
    result = await db.execute(
        select(User).where(User.telegram_id == request.telegram_id)
    )
    user = result.scalar_one_or_none()
    
    if user:
        # Update existing user
        user.phone_number = request.phone
        user.first_name = request.first_name
        user.last_name = request.last_name
        user.username = request.username
        user.loan_amount = loan_data.get("loan_amount")
        user.loan_term = loan_data.get("loan_term")
        user.loan_purpose = loan_data.get("loan_purpose")
        user.monthly_income = loan_data.get("monthly_income")
        user.updated_at = datetime.utcnow()
    else:
        # Create new user
        user = User(
            telegram_id=request.telegram_id,
            phone_number=request.phone,
            first_name=request.first_name,
            last_name=request.last_name,
            username=request.username,
            loan_amount=loan_data.get("loan_amount"),
            loan_term=loan_data.get("loan_term"),
            loan_purpose=loan_data.get("loan_purpose"),
            monthly_income=loan_data.get("monthly_income")
        )
        db.add(user)
    
    await db.commit()
    await db.refresh(user)
    
    # Save token-user mapping for verification
    auth_token_service.set_user_for_token(request.auth_token, user.id)
    
    # Generate return URL
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    return_url = f"{frontend_url}/?auth_token={request.auth_token}"
    
    return BotAuthCompleteResponse(
        success=True,
        frontend_return_url=return_url,
        user_id=user.id
    )


@router.get("/users/{telegram_id}", response_model=BotUserResponse)
async def get_bot_user(
    telegram_id: int,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_bot_token)
):
    """Get user by telegram_id"""
    result = await db.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return BotUserResponse(
        id=user.id,
        telegram_id=user.telegram_id,
        phone_number=user.phone_number,
        first_name=user.first_name,
        last_name=user.last_name,
        username=user.username,
        loan_amount=user.loan_amount,
        loan_term=user.loan_term,
        loan_purpose=user.loan_purpose,
        monthly_income=user.monthly_income,
        created_at=user.created_at,
        updated_at=user.updated_at
    )


@router.get("/health")
async def bot_health_check(_: bool = Depends(verify_bot_token)):
    """Health check endpoint for bot service"""
    return {"status": "ok", "service": "bot-api"}