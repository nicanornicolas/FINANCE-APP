from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID
from enum import Enum


class ReportPeriod(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    CUSTOM = "custom"


class ExportFormat(str, Enum):
    PDF = "pdf"
    CSV = "csv"
    EXCEL = "excel"
    JSON = "json"


class DateRangeFilter(BaseModel):
    start_date: date
    end_date: date
    period: Optional[ReportPeriod] = ReportPeriod.CUSTOM


class ReportFilters(BaseModel):
    date_range: DateRangeFilter
    account_ids: Optional[List[UUID]] = None
    category_ids: Optional[List[UUID]] = None
    transaction_types: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    min_amount: Optional[Decimal] = None
    max_amount: Optional[Decimal] = None


class CategorySummary(BaseModel):
    category_id: Optional[UUID]
    category_name: str
    total_amount: Decimal
    transaction_count: int
    percentage: float
    subcategories: Optional[List['CategorySummary']] = []


class ExpenseSummary(BaseModel):
    total_expenses: Decimal
    total_income: Decimal
    net_income: Decimal
    transaction_count: int
    average_transaction: Decimal
    categories: List[CategorySummary]


class TrendDataPoint(BaseModel):
    period: str
    date: date
    income: Decimal
    expenses: Decimal
    net: Decimal


class FinancialMetrics(BaseModel):
    total_balance: Decimal
    monthly_income: Decimal
    monthly_expenses: Decimal
    monthly_savings: Decimal
    savings_rate: float
    top_expense_category: Optional[str]
    expense_trend: List[TrendDataPoint]
    income_trend: List[TrendDataPoint]


class DashboardData(BaseModel):
    metrics: FinancialMetrics
    recent_transactions: List[Dict[str, Any]]
    category_breakdown: List[CategorySummary]
    monthly_comparison: Dict[str, Decimal]


class ReportRequest(BaseModel):
    filters: ReportFilters
    report_type: str = Field(..., description="Type of report to generate")
    export_format: Optional[ExportFormat] = None
    include_charts: bool = True


class ReportResponse(BaseModel):
    report_id: UUID
    report_type: str
    generated_at: datetime
    filters: ReportFilters
    data: Dict[str, Any]
    export_url: Optional[str] = None


class ChartData(BaseModel):
    labels: List[str]
    datasets: List[Dict[str, Any]]
    chart_type: str
    title: str
    options: Optional[Dict[str, Any]] = None


# Update CategorySummary to handle forward references
CategorySummary.model_rebuild()