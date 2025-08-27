from typing import List, Dict, Any, Optional, Tuple
from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, extract
from collections import defaultdict

from ..models.transaction import Transaction, TransactionType
from ..models.category import Category
from ..models.account import Account
from ..schemas.reporting import (
    ReportFilters, ExpenseSummary, CategorySummary, FinancialMetrics,
    TrendDataPoint, DashboardData, ReportPeriod, ChartData
)


class ReportingService:
    def __init__(self, db: Session):
        self.db = db

    def get_dashboard_data(self, user_id: UUID, filters: Optional[ReportFilters] = None) -> DashboardData:
        """Get comprehensive dashboard data for a user."""
        if not filters:
            # Default to last 30 days
            end_date = date.today()
            start_date = end_date - timedelta(days=30)
            filters = ReportFilters(
                date_range={
                    "start_date": start_date,
                    "end_date": end_date,
                    "period": ReportPeriod.MONTHLY
                }
            )

        metrics = self.get_financial_metrics(user_id, filters)
        recent_transactions = self.get_recent_transactions(user_id, limit=10)
        category_breakdown = self.get_category_breakdown(user_id, filters)
        monthly_comparison = self.get_monthly_comparison(user_id)

        return DashboardData(
            metrics=metrics,
            recent_transactions=recent_transactions,
            category_breakdown=category_breakdown,
            monthly_comparison=monthly_comparison
        )

    def get_financial_metrics(self, user_id: UUID, filters: ReportFilters) -> FinancialMetrics:
        """Calculate key financial metrics for the given period."""
        base_query = self._build_base_query(user_id, filters)
        
        # Calculate totals
        income_total = base_query.filter(
            Transaction.transaction_type == TransactionType.INCOME
        ).with_entities(func.coalesce(func.sum(Transaction.amount), 0)).scalar() or Decimal('0')
        
        expense_total = base_query.filter(
            Transaction.transaction_type == TransactionType.EXPENSE
        ).with_entities(func.coalesce(func.sum(Transaction.amount), 0)).scalar() or Decimal('0')

        # Get total balance across all accounts
        total_balance = self.db.query(func.coalesce(func.sum(Account.balance), 0)).filter(
            Account.user_id == user_id,
            Account.is_active == True
        ).scalar() or Decimal('0')

        # Calculate monthly averages
        days_in_period = (filters.date_range.end_date - filters.date_range.start_date).days
        months_in_period = max(days_in_period / 30.0, 1)
        
        monthly_income = income_total / Decimal(str(months_in_period))
        monthly_expenses = expense_total / Decimal(str(months_in_period))
        monthly_savings = monthly_income - monthly_expenses
        
        savings_rate = float((monthly_savings / monthly_income * 100)) if monthly_income > 0 else 0.0

        # Get top expense category
        top_category = self.db.query(
            Category.name,
            func.sum(Transaction.amount).label('total')
        ).join(
            Transaction, Transaction.category_id == Category.id
        ).filter(
            Category.user_id == user_id,
            Transaction.transaction_type == TransactionType.EXPENSE,
            Transaction.date >= filters.date_range.start_date,
            Transaction.date <= filters.date_range.end_date
        ).group_by(Category.name).order_by(func.sum(Transaction.amount).desc()).first()

        top_expense_category = top_category.name if top_category else None

        # Get trends
        expense_trend = self._get_trend_data(user_id, filters, TransactionType.EXPENSE)
        income_trend = self._get_trend_data(user_id, filters, TransactionType.INCOME)

        return FinancialMetrics(
            total_balance=total_balance,
            monthly_income=monthly_income,
            monthly_expenses=monthly_expenses,
            monthly_savings=monthly_savings,
            savings_rate=savings_rate,
            top_expense_category=top_expense_category,
            expense_trend=expense_trend,
            income_trend=income_trend
        )

    def get_expense_summary(self, user_id: UUID, filters: ReportFilters) -> ExpenseSummary:
        """Generate expense summary with category breakdown."""
        base_query = self._build_base_query(user_id, filters)
        
        # Calculate totals
        expense_total = base_query.filter(
            Transaction.transaction_type == TransactionType.EXPENSE
        ).with_entities(func.coalesce(func.sum(Transaction.amount), 0)).scalar() or Decimal('0')
        
        income_total = base_query.filter(
            Transaction.transaction_type == TransactionType.INCOME
        ).with_entities(func.coalesce(func.sum(Transaction.amount), 0)).scalar() or Decimal('0')

        transaction_count = base_query.count()
        average_transaction = (expense_total + income_total) / transaction_count if transaction_count > 0 else Decimal('0')

        # Get category breakdown
        categories = self.get_category_breakdown(user_id, filters)

        return ExpenseSummary(
            total_expenses=expense_total,
            total_income=income_total,
            net_income=income_total - expense_total,
            transaction_count=transaction_count,
            average_transaction=average_transaction,
            categories=categories
        )

    def get_category_breakdown(self, user_id: UUID, filters: ReportFilters) -> List[CategorySummary]:
        """Get spending breakdown by category."""
        base_query = self._build_base_query(user_id, filters)
        
        # Get category totals
        category_data = base_query.join(
            Category, Transaction.category_id == Category.id, isouter=True
        ).with_entities(
            Category.id,
            Category.name,
            func.coalesce(func.sum(Transaction.amount), 0).label('total'),
            func.count(Transaction.id).label('count')
        ).group_by(Category.id, Category.name).all()

        # Calculate total for percentage calculation
        total_amount = sum(row.total for row in category_data)
        
        categories = []
        for row in category_data:
            category_name = row.name or "Uncategorized"
            percentage = float((row.total / total_amount * 100)) if total_amount > 0 else 0.0
            
            categories.append(CategorySummary(
                category_id=row.id,
                category_name=category_name,
                total_amount=row.total,
                transaction_count=row.count,
                percentage=percentage
            ))

        return sorted(categories, key=lambda x: x.total_amount, reverse=True)

    def get_recent_transactions(self, user_id: UUID, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent transactions for dashboard."""
        transactions = self.db.query(Transaction).join(
            Account, Transaction.account_id == Account.id
        ).filter(
            Account.user_id == user_id
        ).order_by(Transaction.date.desc(), Transaction.created_at.desc()).limit(limit).all()

        return [
            {
                "id": str(t.id),
                "date": t.date.isoformat(),
                "description": t.description,
                "amount": float(t.amount),
                "transaction_type": t.transaction_type.value,
                "category_name": t.category.name if t.category else "Uncategorized"
            }
            for t in transactions
        ]

    def get_monthly_comparison(self, user_id: UUID) -> Dict[str, Decimal]:
        """Compare current month with previous month."""
        today = date.today()
        current_month_start = today.replace(day=1)
        previous_month_end = current_month_start - timedelta(days=1)
        previous_month_start = previous_month_end.replace(day=1)

        # Current month
        current_expenses = self._get_period_total(
            user_id, current_month_start, today, TransactionType.EXPENSE
        )
        current_income = self._get_period_total(
            user_id, current_month_start, today, TransactionType.INCOME
        )

        # Previous month
        previous_expenses = self._get_period_total(
            user_id, previous_month_start, previous_month_end, TransactionType.EXPENSE
        )
        previous_income = self._get_period_total(
            user_id, previous_month_start, previous_month_end, TransactionType.INCOME
        )

        return {
            "current_month_expenses": current_expenses,
            "current_month_income": current_income,
            "previous_month_expenses": previous_expenses,
            "previous_month_income": previous_income,
            "expense_change": current_expenses - previous_expenses,
            "income_change": current_income - previous_income
        }

    def generate_chart_data(self, user_id: UUID, chart_type: str, filters: ReportFilters) -> ChartData:
        """Generate chart data for various chart types."""
        if chart_type == "category_pie":
            return self._generate_category_pie_chart(user_id, filters)
        elif chart_type == "expense_trend":
            return self._generate_trend_chart(user_id, filters, TransactionType.EXPENSE)
        elif chart_type == "income_trend":
            return self._generate_trend_chart(user_id, filters, TransactionType.INCOME)
        elif chart_type == "monthly_comparison":
            return self._generate_monthly_comparison_chart(user_id)
        else:
            raise ValueError(f"Unsupported chart type: {chart_type}")

    def _build_base_query(self, user_id: UUID, filters: ReportFilters):
        """Build base query with common filters."""
        query = self.db.query(Transaction).join(
            Account, Transaction.account_id == Account.id
        ).filter(
            Account.user_id == user_id,
            Transaction.date >= filters.date_range.start_date,
            Transaction.date <= filters.date_range.end_date
        )

        if filters.account_ids:
            query = query.filter(Transaction.account_id.in_(filters.account_ids))
        
        if filters.category_ids:
            query = query.filter(Transaction.category_id.in_(filters.category_ids))
        
        if filters.transaction_types:
            query = query.filter(Transaction.transaction_type.in_(filters.transaction_types))
        
        if filters.tags:
            query = query.filter(Transaction.tags.overlap(filters.tags))
        
        if filters.min_amount:
            query = query.filter(Transaction.amount >= filters.min_amount)
        
        if filters.max_amount:
            query = query.filter(Transaction.amount <= filters.max_amount)

        return query

    def _get_trend_data(self, user_id: UUID, filters: ReportFilters, transaction_type: TransactionType) -> List[TrendDataPoint]:
        """Get trend data for a specific transaction type."""
        base_query = self._build_base_query(user_id, filters).filter(
            Transaction.transaction_type == transaction_type
        )

        # Group by month for trend analysis
        trend_data = base_query.with_entities(
            extract('year', Transaction.date).label('year'),
            extract('month', Transaction.date).label('month'),
            func.sum(Transaction.amount).label('total')
        ).group_by(
            extract('year', Transaction.date),
            extract('month', Transaction.date)
        ).order_by(
            extract('year', Transaction.date),
            extract('month', Transaction.date)
        ).all()

        trends = []
        for row in trend_data:
            period_date = date(int(row.year), int(row.month), 1)
            period_str = period_date.strftime("%Y-%m")
            
            trends.append(TrendDataPoint(
                period=period_str,
                date=period_date,
                income=row.total if transaction_type == TransactionType.INCOME else Decimal('0'),
                expenses=row.total if transaction_type == TransactionType.EXPENSE else Decimal('0'),
                net=row.total if transaction_type == TransactionType.INCOME else -row.total
            ))

        return trends

    def _get_period_total(self, user_id: UUID, start_date: date, end_date: date, transaction_type: TransactionType) -> Decimal:
        """Get total for a specific period and transaction type."""
        total = self.db.query(func.coalesce(func.sum(Transaction.amount), 0)).join(
            Account, Transaction.account_id == Account.id
        ).filter(
            Account.user_id == user_id,
            Transaction.transaction_type == transaction_type,
            Transaction.date >= start_date,
            Transaction.date <= end_date
        ).scalar()
        
        return total or Decimal('0')

    def _generate_category_pie_chart(self, user_id: UUID, filters: ReportFilters) -> ChartData:
        """Generate pie chart data for category breakdown."""
        categories = self.get_category_breakdown(user_id, filters)
        
        return ChartData(
            labels=[cat.category_name for cat in categories],
            datasets=[{
                "data": [float(cat.total_amount) for cat in categories],
                "backgroundColor": [
                    "#FF6384", "#36A2EB", "#FFCE56", "#4BC0C0", "#9966FF",
                    "#FF9F40", "#FF6384", "#C9CBCF", "#4BC0C0", "#FF6384"
                ]
            }],
            chart_type="pie",
            title="Expenses by Category"
        )

    def _generate_trend_chart(self, user_id: UUID, filters: ReportFilters, transaction_type: TransactionType) -> ChartData:
        """Generate line chart for trends."""
        trends = self._get_trend_data(user_id, filters, transaction_type)
        
        chart_title = f"{transaction_type.value.title()} Trend"
        color = "#36A2EB" if transaction_type == TransactionType.INCOME else "#FF6384"
        
        return ChartData(
            labels=[trend.period for trend in trends],
            datasets=[{
                "label": transaction_type.value.title(),
                "data": [float(trend.income if transaction_type == TransactionType.INCOME else trend.expenses) for trend in trends],
                "borderColor": color,
                "backgroundColor": color + "20",
                "fill": True
            }],
            chart_type="line",
            title=chart_title
        )

    def _generate_monthly_comparison_chart(self, user_id: UUID) -> ChartData:
        """Generate bar chart for monthly comparison."""
        comparison = self.get_monthly_comparison(user_id)
        
        return ChartData(
            labels=["Previous Month", "Current Month"],
            datasets=[
                {
                    "label": "Income",
                    "data": [float(comparison["previous_month_income"]), float(comparison["current_month_income"])],
                    "backgroundColor": "#36A2EB"
                },
                {
                    "label": "Expenses",
                    "data": [float(comparison["previous_month_expenses"]), float(comparison["current_month_expenses"])],
                    "backgroundColor": "#FF6384"
                }
            ],
            chart_type="bar",
            title="Monthly Income vs Expenses Comparison"
        )