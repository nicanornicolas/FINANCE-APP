from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from ..models.budget import BudgetPeriod, BudgetStatus, GoalType, GoalStatus, AlertType, AlertStatus


# Budget Schemas
class BudgetCategoryBase(BaseModel):
    category_id: UUID
    allocated_amount: Decimal = Field(..., gt=0, description="Amount allocated to this category")
    warning_threshold: Optional[Decimal] = Field(80.0, ge=0, le=100, description="Warning threshold percentage")
    notes: Optional[str] = None


class BudgetCategoryCreate(BudgetCategoryBase):
    pass


class BudgetCategoryUpdate(BaseModel):
    allocated_amount: Optional[Decimal] = Field(None, gt=0)
    warning_threshold: Optional[Decimal] = Field(None, ge=0, le=100)
    notes: Optional[str] = None


class BudgetCategoryResponse(BudgetCategoryBase):
    id: UUID
    budget_id: UUID
    created_at: datetime
    updated_at: datetime
    
    # Additional computed fields
    spent_amount: Optional[Decimal] = None
    remaining_amount: Optional[Decimal] = None
    percentage_used: Optional[Decimal] = None
    category_name: Optional[str] = None

    class Config:
        from_attributes = True


class BudgetBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    period: BudgetPeriod
    start_date: date
    end_date: Optional[date] = None
    total_amount: Decimal = Field(..., gt=0, description="Total budget amount")
    status: Optional[BudgetStatus] = BudgetStatus.ACTIVE
    is_template: Optional[bool] = False

    @validator('end_date')
    def validate_end_date(cls, v, values):
        if v and 'start_date' in values and v <= values['start_date']:
            raise ValueError('End date must be after start date')
        return v


class BudgetCreate(BudgetBase):
    budget_categories: List[BudgetCategoryCreate] = []


class BudgetUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    period: Optional[BudgetPeriod] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    total_amount: Optional[Decimal] = Field(None, gt=0)
    status: Optional[BudgetStatus] = None
    is_template: Optional[bool] = None


class BudgetResponse(BudgetBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime
    budget_categories: List[BudgetCategoryResponse] = []
    
    # Additional computed fields
    total_spent: Optional[Decimal] = None
    total_remaining: Optional[Decimal] = None
    percentage_used: Optional[Decimal] = None
    is_over_budget: Optional[bool] = None

    class Config:
        from_attributes = True


# Financial Goal Schemas
class GoalMilestoneBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    target_amount: Decimal = Field(..., gt=0)
    target_date: Optional[date] = None
    notes: Optional[str] = None


class GoalMilestoneCreate(GoalMilestoneBase):
    pass


class GoalMilestoneUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    target_amount: Optional[Decimal] = Field(None, gt=0)
    target_date: Optional[date] = None
    notes: Optional[str] = None
    is_achieved: Optional[bool] = None


class GoalMilestoneResponse(GoalMilestoneBase):
    id: UUID
    goal_id: UUID
    achieved_date: Optional[date] = None
    is_achieved: bool
    created_at: datetime

    class Config:
        from_attributes = True


class FinancialGoalBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    goal_type: GoalType
    target_amount: Decimal = Field(..., gt=0)
    target_date: Optional[date] = None
    category_id: Optional[UUID] = None
    status: Optional[GoalStatus] = GoalStatus.ACTIVE
    priority: Optional[int] = Field(1, ge=1, le=10)
    auto_contribute: Optional[bool] = False
    contribution_amount: Optional[Decimal] = Field(None, gt=0)
    contribution_frequency: Optional[BudgetPeriod] = None

    @validator('contribution_amount')
    def validate_contribution_amount(cls, v, values):
        if values.get('auto_contribute') and not v:
            raise ValueError('Contribution amount is required when auto_contribute is enabled')
        return v

    @validator('contribution_frequency')
    def validate_contribution_frequency(cls, v, values):
        if values.get('auto_contribute') and not v:
            raise ValueError('Contribution frequency is required when auto_contribute is enabled')
        return v


class FinancialGoalCreate(FinancialGoalBase):
    goal_milestones: List[GoalMilestoneCreate] = []


class FinancialGoalUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    goal_type: Optional[GoalType] = None
    target_amount: Optional[Decimal] = Field(None, gt=0)
    current_amount: Optional[Decimal] = Field(None, ge=0)
    target_date: Optional[date] = None
    category_id: Optional[UUID] = None
    status: Optional[GoalStatus] = None
    priority: Optional[int] = Field(None, ge=1, le=10)
    auto_contribute: Optional[bool] = None
    contribution_amount: Optional[Decimal] = Field(None, gt=0)
    contribution_frequency: Optional[BudgetPeriod] = None


class FinancialGoalResponse(FinancialGoalBase):
    id: UUID
    user_id: UUID
    current_amount: Decimal
    created_at: datetime
    updated_at: datetime
    goal_milestones: List[GoalMilestoneResponse] = []
    
    # Additional computed fields
    progress_percentage: Optional[Decimal] = None
    remaining_amount: Optional[Decimal] = None
    days_remaining: Optional[int] = None
    monthly_required_contribution: Optional[Decimal] = None
    is_on_track: Optional[bool] = None

    class Config:
        from_attributes = True


# Cash Flow Forecast Schemas
class CashFlowForecastBase(BaseModel):
    forecast_date: date
    predicted_income: Decimal
    predicted_expenses: Decimal
    predicted_balance: Decimal
    confidence_score: Optional[Decimal] = Field(0.0, ge=0, le=100)
    model_version: Optional[str] = None


class CashFlowForecastCreate(CashFlowForecastBase):
    pass


class CashFlowForecastResponse(CashFlowForecastBase):
    id: UUID
    user_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


# Budget Alert Schemas
class BudgetAlertBase(BaseModel):
    alert_type: AlertType
    title: str = Field(..., min_length=1, max_length=255)
    message: str = Field(..., min_length=1)
    severity: Optional[str] = Field("info", regex="^(info|warning|error)$")


class BudgetAlertCreate(BudgetAlertBase):
    budget_id: Optional[UUID] = None
    goal_id: Optional[UUID] = None


class BudgetAlertUpdate(BaseModel):
    status: AlertStatus


class BudgetAlertResponse(BudgetAlertBase):
    id: UUID
    user_id: UUID
    budget_id: Optional[UUID] = None
    goal_id: Optional[UUID] = None
    status: AlertStatus
    triggered_at: datetime
    sent_at: Optional[datetime] = None
    read_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Budget Analysis Schemas
class BudgetAnalysis(BaseModel):
    budget_id: UUID
    period_start: date
    period_end: date
    total_budgeted: Decimal
    total_spent: Decimal
    total_remaining: Decimal
    percentage_used: Decimal
    categories_over_budget: List[UUID] = []
    categories_near_limit: List[UUID] = []
    spending_trend: Optional[str] = None  # "increasing", "decreasing", "stable"


class BudgetVsActualComparison(BaseModel):
    budget_id: UUID
    comparison_period: str
    categories: List[dict]  # Category-wise comparison
    total_variance: Decimal
    variance_percentage: Decimal
    insights: List[str] = []


class CashFlowProjection(BaseModel):
    user_id: UUID
    projection_months: int
    starting_balance: Decimal
    monthly_forecasts: List[CashFlowForecastResponse]
    projected_end_balance: Decimal
    cash_flow_warnings: List[str] = []
    recommendations: List[str] = []


# Request/Response wrapper schemas
class BudgetListResponse(BaseModel):
    budgets: List[BudgetResponse]
    total_count: int
    page: int
    page_size: int


class FinancialGoalListResponse(BaseModel):
    goals: List[FinancialGoalResponse]
    total_count: int
    page: int
    page_size: int


class BudgetAlertListResponse(BaseModel):
    alerts: List[BudgetAlertResponse]
    total_count: int
    unread_count: int
    page: int
    page_size: int