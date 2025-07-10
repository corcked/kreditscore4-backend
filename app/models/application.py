from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, BigInteger, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum


class ApplicationStatus(enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class LoanApplication(Base):
    __tablename__ = "loan_applications"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Loan details
    loan_amount = Column(Float, nullable=False)
    loan_term = Column(Integer, nullable=False)  # в месяцах
    loan_purpose = Column(String(100), nullable=False)
    monthly_income = Column(Float, nullable=False)
    
    # Status
    status = Column(Enum(ApplicationStatus), default=ApplicationStatus.PENDING, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    approved_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Additional info
    rejection_reason = Column(String(500), nullable=True)
    notes = Column(String(1000), nullable=True)
    
    # Relationship
    user = relationship("User", back_populates="applications") 