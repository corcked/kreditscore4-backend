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
    
    bot_username = os.getenv("TELEGRAM_BOT_USERNAME", "kredit_score_bot")
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
        # Create loan application
        from app.models import LoanApplication, ApplicationStatus
        
        application = LoanApplication(
            user_id=user.id,
            loan_amount=loan_data.get("loan_amount"),
            loan_term=loan_data.get("loan_term"),
            loan_purpose=loan_data.get("loan_purpose"),
            monthly_income=loan_data.get("monthly_income"),
            status=ApplicationStatus.PENDING
        )
        db.add(application)
        user.updated_at = datetime.utcnow()
    else:
        # Create new user
        user = User(
            telegram_id=request.telegram_id,
            phone_number=request.phone,
            first_name=request.first_name,
            last_name=request.last_name,
            username=request.username
        )
        db.add(user)
        await db.flush()  # Get user.id
        
        # Create loan application for new user
        from app.models import LoanApplication, ApplicationStatus
        
        application = LoanApplication(
            user_id=user.id,
            loan_amount=loan_data.get("loan_amount"),
            loan_term=loan_data.get("loan_term"),
            loan_purpose=loan_data.get("loan_purpose"),
            monthly_income=loan_data.get("monthly_income"),
            status=ApplicationStatus.PENDING
        )
        db.add(application)
    
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


@router.get("/users/{telegram_id}")
async def get_bot_user(
    telegram_id: int,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_bot_token)
):
    """Get user by telegram_id"""
    from sqlalchemy.orm import selectinload
    
    result = await db.execute(
        select(User).where(User.telegram_id == telegram_id).options(selectinload(User.applications))
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get latest application if exists
    latest_application = user.applications[0] if user.applications else None
    
    return {
        "id": user.id,
        "telegram_id": user.telegram_id,
        "phone_number": user.phone_number,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "username": user.username,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
        "applications": [
            {
                "id": app.id,
                "loan_amount": app.loan_amount,
                "loan_term": app.loan_term,
                "loan_purpose": app.loan_purpose,
                "monthly_income": app.monthly_income,
                "status": app.status.value,
                "created_at": app.created_at
            }
            for app in user.applications
        ],
        # For backward compatibility
        "loan_amount": latest_application.loan_amount if latest_application else None,
        "loan_term": latest_application.loan_term if latest_application else None,
        "loan_purpose": latest_application.loan_purpose if latest_application else None,
        "monthly_income": latest_application.monthly_income if latest_application else None
    }


@router.get("/health")
async def bot_health_check(_: bool = Depends(verify_bot_token)):
    """Health check endpoint for bot service"""
    return {"status": "ok", "service": "bot-api"}