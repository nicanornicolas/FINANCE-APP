from sqlalchemy import Column, String, Boolean, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from ..db.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    settings = Column(Text)  # JSON string for user settings

    # Relationships
    accounts = relationship("Account", back_populates="user", cascade="all, delete-orphan")
    categories = relationship("Category", back_populates="user", cascade="all, delete-orphan")
    tax_filings = relationship("TaxFiling", back_populates="user", cascade="all, delete-orphan")
    kra_taxpayer = relationship("KRATaxpayer", back_populates="user", uselist=False, cascade="all, delete-orphan")
    business_entities = relationship("BusinessEntity", back_populates="user", cascade="all, delete-orphan")
    budgets = relationship("Budget", back_populates="user", cascade="all, delete-orphan")
    financial_goals = relationship("FinancialGoal", back_populates="user", cascade="all, delete-orphan")
    cash_flow_forecasts = relationship("CashFlowForecast", back_populates="user", cascade="all, delete-orphan")
    budget_alerts = relationship("BudgetAlert", back_populates="user", cascade="all, delete-orphan")
    
    # Security relationships
    mfa_methods = relationship("MFAMethod", back_populates="user", cascade="all, delete-orphan")
    roles = relationship("Role", secondary="user_roles", back_populates="users")

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email})>"