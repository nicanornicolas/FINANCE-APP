import pytest
from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4
from unittest.mock import Mock, patch

from app.services.reporting import ReportingService
from app.schemas.reporting import ReportFilters, DateRangeFilter, ReportPeriod
from app.models.transaction import Transaction, TransactionType
from app.models.category import Category
from app.models.account import Account
from app.models.user import User


class TestReportingService:
    """Test suite for ReportingService."""

    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock()

    @pytest.fixture
    def reporting_service(self, mock_db):
        """Create ReportingService instance with mocked database."""
        return ReportingService(mock_db)

    @pytest.fixture
    def sample_user_id(self):
        """Sample user ID for testing."""
        return uuid4()

    @pytest.fixture
    def sample_filters(self):
        """Sample report filters for testing."""
        return ReportFilters(
            date_range=DateRangeFilter(
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 31),
                period=ReportPeriod.MONTHLY
            )
        )

    @pytest.fixture
    def sample_transactions(self):
        """Sample transaction data for testing."""
        return [
            {
                'id': uuid4(),
                'amount': Decimal('100.00'),
                'transaction_type': TransactionType.EXPENSE,
                'date': date(2024, 1, 15),
                'description': 'Grocery Store',
                'category_name': 'Food'
            },
            {
                'id': uuid4(),
                'amount': Decimal('2000.00'),
                'transaction_type': TransactionType.INCOME,
                'date': date(2024, 1, 1),
                'description': 'Salary',
                'category_name': 'Income'
            },
            {
                'id': uuid4(),
                'amount': Decimal('50.00'),
                'transaction_type': TransactionType.EXPENSE,
                'date': date(2024, 1, 20),
                'description': 'Gas Station',
                'category_name': 'Transportation'
            }
        ]

    def test_get_financial_metrics_calculation(self, reporting_service, mock_db, sample_user_id, sample_filters):
        """Test financial metrics calculation."""
        # Mock database queries
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        
        # Mock income total
        mock_query.filter.return_value.with_entities.return_value.scalar.return_value = Decimal('2000.00')
        
        # Mock expense total (second call)
        expense_query = Mock()
        expense_query.filter.return_value.with_entities.return_value.scalar.return_value = Decimal('150.00')
        mock_db.query.side_effect = [mock_query, expense_query, Mock()]  # Third for balance query
        
        # Mock balance query
        balance_query = Mock()
        balance_query.filter.return_value.scalar.return_value = Decimal('5000.00')
        mock_db.query.side_effect = [mock_query, expense_query, balance_query]
        
        # Mock trend data
        with patch.object(reporting_service, '_get_trend_data') as mock_trend:
            mock_trend.return_value = []
            
            metrics = reporting_service.get_financial_metrics(sample_user_id, sample_filters)
            
            assert metrics.monthly_income == Decimal('2000.00')
            assert metrics.monthly_expenses == Decimal('150.00')
            assert metrics.monthly_savings == Decimal('1850.00')
            assert metrics.total_balance == Decimal('5000.00')
            assert metrics.savings_rate == 92.5  # (1850/2000) * 100

    def test_get_expense_summary(self, reporting_service, mock_db, sample_user_id, sample_filters):
        """Test expense summary generation."""
        # Mock base query
        mock_base_query = Mock()
        
        with patch.object(reporting_service, '_build_base_query') as mock_build_query:
            mock_build_query.return_value = mock_base_query
            
            # Mock expense total
            expense_filter = Mock()
            expense_filter.with_entities.return_value.scalar.return_value = Decimal('150.00')
            mock_base_query.filter.return_value = expense_filter
            
            # Mock income total (second call to filter)
            income_filter = Mock()
            income_filter.with_entities.return_value.scalar.return_value = Decimal('2000.00')
            mock_base_query.filter.side_effect = [expense_filter, income_filter]
            
            # Mock transaction count
            mock_base_query.count.return_value = 3
            
            # Mock category breakdown
            with patch.object(reporting_service, 'get_category_breakdown') as mock_categories:
                mock_categories.return_value = []
                
                summary = reporting_service.get_expense_summary(sample_user_id, sample_filters)
                
                assert summary.total_expenses == Decimal('150.00')
                assert summary.total_income == Decimal('2000.00')
                assert summary.net_income == Decimal('1850.00')
                assert summary.transaction_count == 3
                assert summary.average_transaction == Decimal('716.67')  # (150+2000)/3

    def test_get_category_breakdown(self, reporting_service, mock_db, sample_user_id, sample_filters):
        """Test category breakdown calculation."""
        # Mock base query and join
        mock_base_query = Mock()
        mock_join_query = Mock()
        
        with patch.object(reporting_service, '_build_base_query') as mock_build_query:
            mock_build_query.return_value = mock_base_query
            mock_base_query.join.return_value = mock_join_query
            
            # Mock category data
            mock_category_data = [
                Mock(id=uuid4(), name='Food', total=Decimal('100.00'), count=1),
                Mock(id=uuid4(), name='Transportation', total=Decimal('50.00'), count=1),
                Mock(id=None, name=None, total=Decimal('25.00'), count=1)  # Uncategorized
            ]
            mock_join_query.with_entities.return_value.group_by.return_value.all.return_value = mock_category_data
            
            categories = reporting_service.get_category_breakdown(sample_user_id, sample_filters)
            
            assert len(categories) == 3
            assert categories[0].category_name == 'Food'
            assert categories[0].total_amount == Decimal('100.00')
            assert categories[0].percentage == pytest.approx(57.14, rel=1e-2)  # 100/175 * 100
            
            assert categories[2].category_name == 'Uncategorized'
            assert categories[2].total_amount == Decimal('25.00')

    def test_get_recent_transactions(self, reporting_service, mock_db, sample_user_id):
        """Test recent transactions retrieval."""
        # Mock query chain
        mock_query = Mock()
        mock_join = Mock()
        mock_filter = Mock()
        mock_order = Mock()
        mock_limit = Mock()
        
        mock_db.query.return_value = mock_query
        mock_query.join.return_value = mock_join
        mock_join.filter.return_value = mock_filter
        mock_filter.order_by.return_value = mock_order
        mock_order.limit.return_value = mock_limit
        
        # Mock transaction objects
        mock_transaction = Mock()
        mock_transaction.id = uuid4()
        mock_transaction.date = date(2024, 1, 15)
        mock_transaction.description = 'Test Transaction'
        mock_transaction.amount = Decimal('100.00')
        mock_transaction.transaction_type = TransactionType.EXPENSE
        mock_transaction.category = Mock(name='Food')
        
        mock_limit.all.return_value = [mock_transaction]
        
        transactions = reporting_service.get_recent_transactions(sample_user_id, limit=5)
        
        assert len(transactions) == 1
        assert transactions[0]['description'] == 'Test Transaction'
        assert transactions[0]['amount'] == 100.0
        assert transactions[0]['transaction_type'] == 'expense'
        assert transactions[0]['category_name'] == 'Food'

    def test_get_monthly_comparison(self, reporting_service, sample_user_id):
        """Test monthly comparison calculation."""
        with patch.object(reporting_service, '_get_period_total') as mock_get_total:
            # Mock period totals
            mock_get_total.side_effect = [
                Decimal('1500.00'),  # current expenses
                Decimal('2000.00'),  # current income
                Decimal('1200.00'),  # previous expenses
                Decimal('1800.00')   # previous income
            ]
            
            comparison = reporting_service.get_monthly_comparison(sample_user_id)
            
            assert comparison['current_month_expenses'] == Decimal('1500.00')
            assert comparison['current_month_income'] == Decimal('2000.00')
            assert comparison['previous_month_expenses'] == Decimal('1200.00')
            assert comparison['previous_month_income'] == Decimal('1800.00')
            assert comparison['expense_change'] == Decimal('300.00')
            assert comparison['income_change'] == Decimal('200.00')

    def test_generate_chart_data_category_pie(self, reporting_service, sample_user_id, sample_filters):
        """Test category pie chart data generation."""
        mock_categories = [
            Mock(category_name='Food', total_amount=Decimal('100.00')),
            Mock(category_name='Transportation', total_amount=Decimal('50.00'))
        ]
        
        with patch.object(reporting_service, 'get_category_breakdown') as mock_breakdown:
            mock_breakdown.return_value = mock_categories
            
            chart_data = reporting_service.generate_chart_data(sample_user_id, 'category_pie', sample_filters)
            
            assert chart_data.chart_type == 'pie'
            assert chart_data.title == 'Expenses by Category'
            assert chart_data.labels == ['Food', 'Transportation']
            assert len(chart_data.datasets) == 1
            assert chart_data.datasets[0]['data'] == [100.0, 50.0]

    def test_generate_chart_data_invalid_type(self, reporting_service, sample_user_id, sample_filters):
        """Test chart data generation with invalid chart type."""
        with pytest.raises(ValueError, match="Unsupported chart type"):
            reporting_service.generate_chart_data(sample_user_id, 'invalid_type', sample_filters)

    def test_build_base_query_with_filters(self, reporting_service, mock_db, sample_user_id, sample_filters):
        """Test base query building with various filters."""
        # Add additional filters
        sample_filters.account_ids = [uuid4()]
        sample_filters.category_ids = [uuid4()]
        sample_filters.transaction_types = ['expense']
        sample_filters.tags = ['business']
        sample_filters.min_amount = Decimal('10.00')
        sample_filters.max_amount = Decimal('1000.00')
        
        # Mock query chain
        mock_query = Mock()
        mock_join = Mock()
        mock_filter = Mock()
        
        mock_db.query.return_value = mock_query
        mock_query.join.return_value = mock_join
        mock_join.filter.return_value = mock_filter
        
        # Mock filter method to return itself for chaining
        mock_filter.filter.return_value = mock_filter
        
        result = reporting_service._build_base_query(sample_user_id, sample_filters)
        
        # Verify that filters were applied
        assert mock_filter.filter.call_count >= 6  # All filters should be applied

    def test_get_trend_data(self, reporting_service, mock_db, sample_user_id, sample_filters):
        """Test trend data generation."""
        # Mock base query
        mock_base_query = Mock()
        mock_filter = Mock()
        mock_entities = Mock()
        mock_group = Mock()
        mock_order = Mock()
        
        with patch.object(reporting_service, '_build_base_query') as mock_build_query:
            mock_build_query.return_value = mock_base_query
            mock_base_query.filter.return_value = mock_filter
            mock_filter.with_entities.return_value = mock_entities
            mock_entities.group_by.return_value = mock_group
            mock_group.order_by.return_value = mock_order
            
            # Mock trend data
            mock_trend_row = Mock()
            mock_trend_row.year = 2024
            mock_trend_row.month = 1
            mock_trend_row.total = Decimal('1500.00')
            
            mock_order.all.return_value = [mock_trend_row]
            
            trends = reporting_service._get_trend_data(sample_user_id, sample_filters, TransactionType.EXPENSE)
            
            assert len(trends) == 1
            assert trends[0].period == '2024-01'
            assert trends[0].expenses == Decimal('1500.00')
            assert trends[0].income == Decimal('0')

    def test_get_period_total(self, reporting_service, mock_db, sample_user_id):
        """Test period total calculation."""
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 31)
        
        # Mock query chain
        mock_query = Mock()
        mock_join = Mock()
        mock_filter = Mock()
        
        mock_db.query.return_value = mock_query
        mock_query.join.return_value = mock_join
        mock_join.filter.return_value = mock_filter
        mock_filter.scalar.return_value = Decimal('1500.00')
        
        total = reporting_service._get_period_total(
            sample_user_id, start_date, end_date, TransactionType.EXPENSE
        )
        
        assert total == Decimal('1500.00')

    def test_get_period_total_none_result(self, reporting_service, mock_db, sample_user_id):
        """Test period total calculation when query returns None."""
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 31)
        
        # Mock query chain returning None
        mock_query = Mock()
        mock_join = Mock()
        mock_filter = Mock()
        
        mock_db.query.return_value = mock_query
        mock_query.join.return_value = mock_join
        mock_join.filter.return_value = mock_filter
        mock_filter.scalar.return_value = None
        
        total = reporting_service._get_period_total(
            sample_user_id, start_date, end_date, TransactionType.EXPENSE
        )
        
        assert total == Decimal('0')

    def test_dashboard_data_integration(self, reporting_service, sample_user_id):
        """Test dashboard data integration with all components."""
        with patch.object(reporting_service, 'get_financial_metrics') as mock_metrics, \
             patch.object(reporting_service, 'get_recent_transactions') as mock_transactions, \
             patch.object(reporting_service, 'get_category_breakdown') as mock_categories, \
             patch.object(reporting_service, 'get_monthly_comparison') as mock_comparison:
            
            # Mock return values
            mock_metrics.return_value = Mock()
            mock_transactions.return_value = []
            mock_categories.return_value = []
            mock_comparison.return_value = {}
            
            dashboard_data = reporting_service.get_dashboard_data(sample_user_id)
            
            # Verify all components were called
            mock_metrics.assert_called_once()
            mock_transactions.assert_called_once_with(sample_user_id, limit=10)
            mock_categories.assert_called_once()
            mock_comparison.assert_called_once_with(sample_user_id)
            
            # Verify dashboard data structure
            assert hasattr(dashboard_data, 'metrics')
            assert hasattr(dashboard_data, 'recent_transactions')
            assert hasattr(dashboard_data, 'category_breakdown')
            assert hasattr(dashboard_data, 'monthly_comparison')