import pytest
from datetime import date
from decimal import Decimal
from uuid import uuid4

from app.schemas.reporting import (
    DateRangeFilter, ReportFilters, CategorySummary, ExpenseSummary,
    FinancialMetrics, TrendDataPoint, ChartData, ReportPeriod, ExportFormat
)


class TestReportingSchemas:
    """Test suite for reporting schemas."""

    def test_date_range_filter_creation(self):
        """Test DateRangeFilter schema creation."""
        filter_data = DateRangeFilter(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            period=ReportPeriod.MONTHLY
        )
        
        assert filter_data.start_date == date(2024, 1, 1)
        assert filter_data.end_date == date(2024, 1, 31)
        assert filter_data.period == ReportPeriod.MONTHLY

    def test_report_filters_creation(self):
        """Test ReportFilters schema creation."""
        date_range = DateRangeFilter(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31)
        )
        
        filters = ReportFilters(
            date_range=date_range,
            account_ids=[uuid4()],
            category_ids=[uuid4()],
            transaction_types=['expense', 'income'],
            tags=['business'],
            min_amount=Decimal('10.00'),
            max_amount=Decimal('1000.00')
        )
        
        assert filters.date_range == date_range
        assert len(filters.account_ids) == 1
        assert len(filters.category_ids) == 1
        assert filters.transaction_types == ['expense', 'income']
        assert filters.tags == ['business']
        assert filters.min_amount == Decimal('10.00')
        assert filters.max_amount == Decimal('1000.00')

    def test_category_summary_creation(self):
        """Test CategorySummary schema creation."""
        category = CategorySummary(
            category_id=uuid4(),
            category_name='Food',
            total_amount=Decimal('500.00'),
            transaction_count=10,
            percentage=25.5
        )
        
        assert category.category_name == 'Food'
        assert category.total_amount == Decimal('500.00')
        assert category.transaction_count == 10
        assert category.percentage == 25.5

    def test_category_summary_with_subcategories(self):
        """Test CategorySummary with subcategories."""
        subcategory = CategorySummary(
            category_id=uuid4(),
            category_name='Restaurants',
            total_amount=Decimal('200.00'),
            transaction_count=5,
            percentage=10.0
        )
        
        category = CategorySummary(
            category_id=uuid4(),
            category_name='Food',
            total_amount=Decimal('500.00'),
            transaction_count=10,
            percentage=25.5,
            subcategories=[subcategory]
        )
        
        assert len(category.subcategories) == 1
        assert category.subcategories[0].category_name == 'Restaurants'

    def test_expense_summary_creation(self):
        """Test ExpenseSummary schema creation."""
        categories = [
            CategorySummary(
                category_id=uuid4(),
                category_name='Food',
                total_amount=Decimal('500.00'),
                transaction_count=10,
                percentage=50.0
            )
        ]
        
        summary = ExpenseSummary(
            total_expenses=Decimal('1000.00'),
            total_income=Decimal('3000.00'),
            net_income=Decimal('2000.00'),
            transaction_count=15,
            average_transaction=Decimal('266.67'),
            categories=categories
        )
        
        assert summary.total_expenses == Decimal('1000.00')
        assert summary.total_income == Decimal('3000.00')
        assert summary.net_income == Decimal('2000.00')
        assert summary.transaction_count == 15
        assert summary.average_transaction == Decimal('266.67')
        assert len(summary.categories) == 1

    def test_trend_data_point_creation(self):
        """Test TrendDataPoint schema creation."""
        trend = TrendDataPoint(
            period='2024-01',
            date=date(2024, 1, 1),
            income=Decimal('3000.00'),
            expenses=Decimal('1000.00'),
            net=Decimal('2000.00')
        )
        
        assert trend.period == '2024-01'
        assert trend.date == date(2024, 1, 1)
        assert trend.income == Decimal('3000.00')
        assert trend.expenses == Decimal('1000.00')
        assert trend.net == Decimal('2000.00')

    def test_financial_metrics_creation(self):
        """Test FinancialMetrics schema creation."""
        expense_trend = [
            TrendDataPoint(
                period='2024-01',
                date=date(2024, 1, 1),
                income=Decimal('0'),
                expenses=Decimal('1000.00'),
                net=Decimal('-1000.00')
            )
        ]
        
        income_trend = [
            TrendDataPoint(
                period='2024-01',
                date=date(2024, 1, 1),
                income=Decimal('3000.00'),
                expenses=Decimal('0'),
                net=Decimal('3000.00')
            )
        ]
        
        metrics = FinancialMetrics(
            total_balance=Decimal('5000.00'),
            monthly_income=Decimal('3000.00'),
            monthly_expenses=Decimal('1000.00'),
            monthly_savings=Decimal('2000.00'),
            savings_rate=66.67,
            top_expense_category='Food',
            expense_trend=expense_trend,
            income_trend=income_trend
        )
        
        assert metrics.total_balance == Decimal('5000.00')
        assert metrics.monthly_income == Decimal('3000.00')
        assert metrics.monthly_expenses == Decimal('1000.00')
        assert metrics.monthly_savings == Decimal('2000.00')
        assert metrics.savings_rate == 66.67
        assert metrics.top_expense_category == 'Food'
        assert len(metrics.expense_trend) == 1
        assert len(metrics.income_trend) == 1

    def test_chart_data_creation(self):
        """Test ChartData schema creation."""
        chart = ChartData(
            labels=['Food', 'Transportation', 'Entertainment'],
            datasets=[{
                'data': [500, 300, 200],
                'backgroundColor': ['#FF6384', '#36A2EB', '#FFCE56']
            }],
            chart_type='pie',
            title='Expenses by Category',
            options={'responsive': True}
        )
        
        assert chart.labels == ['Food', 'Transportation', 'Entertainment']
        assert len(chart.datasets) == 1
        assert chart.chart_type == 'pie'
        assert chart.title == 'Expenses by Category'
        assert chart.options['responsive'] is True

    def test_export_format_enum(self):
        """Test ExportFormat enum values."""
        assert ExportFormat.PDF == 'pdf'
        assert ExportFormat.CSV == 'csv'
        assert ExportFormat.EXCEL == 'excel'
        assert ExportFormat.JSON == 'json'

    def test_report_period_enum(self):
        """Test ReportPeriod enum values."""
        assert ReportPeriod.DAILY == 'daily'
        assert ReportPeriod.WEEKLY == 'weekly'
        assert ReportPeriod.MONTHLY == 'monthly'
        assert ReportPeriod.QUARTERLY == 'quarterly'
        assert ReportPeriod.YEARLY == 'yearly'
        assert ReportPeriod.CUSTOM == 'custom'

    def test_category_summary_model_rebuild(self):
        """Test that CategorySummary handles forward references correctly."""
        # This tests the model_rebuild() call at the end of the schema file
        parent_category = CategorySummary(
            category_id=uuid4(),
            category_name='Food',
            total_amount=Decimal('500.00'),
            transaction_count=10,
            percentage=50.0,
            subcategories=[]
        )
        
        subcategory = CategorySummary(
            category_id=uuid4(),
            category_name='Restaurants',
            total_amount=Decimal('200.00'),
            transaction_count=5,
            percentage=20.0
        )
        
        parent_category.subcategories = [subcategory]
        
        assert len(parent_category.subcategories) == 1
        assert isinstance(parent_category.subcategories[0], CategorySummary)

    def test_optional_fields(self):
        """Test schemas with optional fields."""
        # Test CategorySummary without category_id (for uncategorized)
        category = CategorySummary(
            category_name='Uncategorized',
            total_amount=Decimal('100.00'),
            transaction_count=2,
            percentage=10.0
        )
        
        assert category.category_id is None
        assert category.category_name == 'Uncategorized'
        
        # Test FinancialMetrics without top_expense_category
        metrics = FinancialMetrics(
            total_balance=Decimal('1000.00'),
            monthly_income=Decimal('2000.00'),
            monthly_expenses=Decimal('1500.00'),
            monthly_savings=Decimal('500.00'),
            savings_rate=25.0,
            expense_trend=[],
            income_trend=[]
        )
        
        assert metrics.top_expense_category is None

    def test_decimal_precision(self):
        """Test that Decimal fields maintain precision."""
        category = CategorySummary(
            category_name='Test',
            total_amount=Decimal('123.456'),
            transaction_count=1,
            percentage=12.345
        )
        
        assert category.total_amount == Decimal('123.456')
        assert category.percentage == 12.345

    def test_date_serialization(self):
        """Test that date fields serialize correctly."""
        trend = TrendDataPoint(
            period='2024-01',
            date=date(2024, 1, 15),
            income=Decimal('1000.00'),
            expenses=Decimal('500.00'),
            net=Decimal('500.00')
        )
        
        # Test model dump
        data = trend.model_dump()
        assert data['date'] == date(2024, 1, 15)
        assert data['period'] == '2024-01'