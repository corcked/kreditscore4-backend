from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from app.database import get_db
from app.models import User, LoanApplication, ApplicationStatus
from app.models.schemas import Token
from app.api.auth import get_current_user


router = APIRouter(prefix="/applications", tags=["applications"])


@router.post("/")
async def create_application(
    loan_amount: float,
    loan_term: int,
    loan_purpose: str,
    monthly_income: float,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new loan application"""
    # Create new application
    application = LoanApplication(
        user_id=current_user.id,
        loan_amount=loan_amount,
        loan_term=loan_term,
        loan_purpose=loan_purpose,
        monthly_income=monthly_income,
        status=ApplicationStatus.PENDING
    )
    
    db.add(application)
    db.commit()
    db.refresh(application)
    
    return {
        "id": application.id,
        "loan_amount": application.loan_amount,
        "loan_term": application.loan_term,
        "status": application.status.value,
        "created_at": application.created_at
    }


@router.get("/")
async def get_applications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all applications for current user"""
    applications = db.query(LoanApplication).filter(
        LoanApplication.user_id == current_user.id
    ).order_by(LoanApplication.created_at.desc()).all()
    
    return [
        {
            "id": app.id,
            "loan_amount": app.loan_amount,
            "loan_term": app.loan_term,
            "loan_purpose": app.loan_purpose,
            "monthly_income": app.monthly_income,
            "status": app.status.value,
            "created_at": app.created_at,
            "updated_at": app.updated_at
        }
        for app in applications
    ]


@router.get("/{application_id}")
async def get_application(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get specific application"""
    application = db.query(LoanApplication).filter(
        LoanApplication.id == application_id,
        LoanApplication.user_id == current_user.id
    ).first()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    return {
        "id": application.id,
        "loan_amount": application.loan_amount,
        "loan_term": application.loan_term,
        "loan_purpose": application.loan_purpose,
        "monthly_income": application.monthly_income,
        "status": application.status.value,
        "created_at": application.created_at,
        "updated_at": application.updated_at,
        "approved_at": application.approved_at,
        "completed_at": application.completed_at,
        "rejection_reason": application.rejection_reason,
        "notes": application.notes
    } 