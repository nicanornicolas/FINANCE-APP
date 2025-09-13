from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Enum, Numeric, Date, Text, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum

from ..db.database import Base


class BudgetPeriod(enum.Enum):
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class BudgetStatus(enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"


class GoalType(enum.Enum):
    SAVINGS = "savings"
    DEBT_PAYOFF = "debt_payoff"
    INVESTMENT = "investment"
    EMERGENCY_FUND = "emergency_fund"
    CUSTOM = "custom"


class GoalStatus(enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class AlertType(enum.Enum):
    BUDGET_EXCEEDED = "budget_exceeded"
    BUDGET_WARNING = "budget_warning"
    GOAL_MILESTONE = "goal_milestone"
    CASH_FLOW_WARNING = "cash_flow_warning"


class AlertStatus(enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    READ = "read"
    DISMISSED = "dismissed"


class Budget(Base):
    __tablename__ = "budgets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    period = Column(Enum(BudgetPeriod), nullable=False, default=BudgetPeriod.MONTHLY)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)  # Null for ongoing budgets
    total_amount = Column(Numeric(precision=12, scale=2), nullable=False)
    status = Column(Enum(BudgetStatus), nullable=False, default=BudgetStatus.ACTIVE)
    is_template = Column(Boolean, default=False)  # For reusable budget templates
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="budgets")
    budget_categories = relationship("BudgetCategory", back_populates="budget", cascade="all, delete-orphan")
    budget_alerts = relationship("BudgetAlert", back_populates="budget", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Budget(id={self.id}, name={self.name}, user_id={self.user_id})>"


class BudgetCategory(Base):
    __tablename__ = "budget_categories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    budget_id = Column(UUID(as_uuid=True), ForeignKey("budgets.id"), nullable=False, index=True)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id"), nullable=False, index=True)
    allocated_amount = Column(Numeric(precision=12, scale=2), nullable=False)
    warning_threshold = Column(Numeric(precision=5, scale=2), default=80.0)  # Percentage (80%)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    budget = relationship("Budget", back_populates="budget_categories")
    category = relationship("Category")

    def __repr__(self):
        return f"<BudgetCategory(id={self.id}, budget_id={self.budget_id}, category_id={self.category_id})>"


class FinancialGoal(Base):
    __tablename__ = "financial_goals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    goal_type = Column(Enum(GoalType), nullable=False)
    target_amount = Column(Numeric(precision=12, scale=2), nullable=False)
    current_amount = Column(Numeric(precision=12, scale=2), default=0.0)
    target_date = Column(Date, nullable=True)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id"), nullable=True)  # Optional category link
    status = Column(Enum(GoalStatus), nullable=False, default=GoalStatus.ACTIVE)
    priority = Column(Integer, default=1)  # 1 = highest priority
    auto_contribute = Column(Boolean, default=False)  # Auto-contribute from transactions
    contribution_amount = Column(Numeric(precision=12, scale=2), nullable=True)  # Regular contribution amount
    contribution_frequency = Column(Enum(BudgetPeriod), nullable=True)  # How often to contribute
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="financial_goals")
    category = relationship("Category")
    goal_milestones = relationship("GoalMilestone", back_populates="goal", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<FinancialGoal(id={self.id}, name={self.name}, user_id={self.user_id})>"


class GoalMilestone(Base):
    __tablename__ = "goal_milestones"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    goal_id = Column(UUID(as_uuid=True), ForeignKey("financial_goals.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    target_amount = Column(Numeric(precision=12, scale=2), nullable=False)
    target_date = Column(Date, nullable=True)
    achieved_date = Column(Date, nullable=True)
    is_achieved = Column(Boolean, default=False)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    goal = relationship("FinancialGoal", back_populates="goal_milestones")

    def __repr__(self):
        return f"<GoalMilestone(id={self.id}, name={self.name}, goal_id={self.goal_id})>"


class CashFlowForecast(Base):
    __tablename__ = "cash_flow_forecasts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    forecast_date = Column(Date, nullable=False, index=True)
    predicted_income = Column(Numeric(precision=12, scale=2), nullable=False)
    predicted_expenses = Column(Numeric(precision=12, scale=2), nullable=False)
    predicted_balance = Column(Numeric(precision=12, scale=2), nullable=False)
    confidence_score = Column(Numeric(precision=5, scale=2), default=0.0)  # 0-100%
    model_version = Column(String, nullable=True)  # Track which model generated this
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="cash_flow_forecasts")

    def __repr__(self):
        return f"<CashFlowForecast(id={self.id}, forecast_date={self.forecast_date}, user_id={self.user_id})>"


class BudgetAlert(Base):
    __tablename__ = "budget_alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    budget_id = Column(UUID(as_uuid=True), ForeignKey("budgets.id"), nullable=True, index=True)
    goal_id = Column(UUID(as_uuid=True), ForeignKey("financial_goals.id"), nullable=True, index=True)
    alert_type = Column(Enum(AlertType), nullable=False)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    severity = Column(String, default="info")  # info, warning, error
    status = Column(Enum(AlertStatus), nullable=False, default=AlertStatus.PENDING)
    triggered_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    read_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", back_populates="budget_alerts")
    budget = relationship("Budget", back_populates="budget_alerts")
    goal = relationship("FinancialGoal")

    def __repr__(self):
        return f"<BudgetAlert(id={self.id}, alert_type={self.alert_type}, user_id={self.user_id})>"