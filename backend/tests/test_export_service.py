import pytest
from decimal import Decimal
from uuid import uuid4
from unittest.mock import Mock, patch
import io

from app.services.export import ExportService
from app.schemas.reporting import ExportFormat, ExpenseSummary, FinancialMetrics, CategorySummary, TrendDataPoint


class TestExportService:
    """Test suite for ExportService."""

    @pytest.fixture
    def export_service(self):
        """Create ExportService instance."""
        return ExportService()

    @pytest.fixture
    def sample_expense_summary(self):
        """Sample expense summary for testing."""
        categories = [
            CategorySummary(
                category_id=uuid4(),
                category_name='Food',
                total_amount=Decimal('500.00'),
                transaction_count=10,
                percentage=50.0
            ),
            CategorySummary(
                category_id=uuid4(),
                category_name='Transportation',
                total_amount=Decimal('300.00'),
                transaction_count=5,
                percentage=30.0
            ),
            CategorySummary(
                category_id=uuid4(),
                category_name='Entertainment',
                total_amount=Decimal('200.00'),
                transaction_count=3,
                percentage=20.0
            )
        ]
        
        return ExpenseSummary(
            total_expenses=Decimal('1000.00'),
            total_income=Decimal('3000.00'),
            net_income=Decimal('2000.00'),
            transaction_count=18,
            average_transaction=Decimal('222.22'),
            categories=categories
        )

    @pytest.fixture
    def sample_financial_metrics(self):
        """Sample financial metrics for testing."""
        expense_trend = [
            TrendDataPoint(
                period='2024-01',
                date='2024-01-01',
                income=Decimal('0'),
                expenses=Decimal('800.00'),
                net=Decimal('-800.00')
            ),
            TrendDataPoint(
                period='2024-02',
                date='2024-02-01',
                income=Decimal('0'),
                expenses=Decimal('900.00'),
                net=Decimal('-900.00')
            )
        ]
        
        income_trend = [
            TrendDataPoint(
                period='2024-01',
                date='2024-01-01',
                income=Decimal('3000.00'),
                expenses=Decimal('0'),
                net=Decimal('3000.00')
            ),
            TrendDataPoint(
                period='2024-02',
                date='2024-02-01',
                income=Decimal('3200.00'),
                expenses=Decimal('0'),
                net=Decimal('3200.00')
            )
        ]
        
        return FinancialMetrics(
            total_balance=Decimal('5000.00'),
            monthly_income=Decimal('3100.00'),
            monthly_expenses=Decimal('850.00'),
            monthly_savings=Decimal('2250.00'),
            savings_rate=72.6,
            top_expense_category='Food',
            expense_trend=expense_trend,
            income_trend=income_trend
        )

    @pytest.fixture
    def sample_transactions(self):
        """Sample transaction data for testing."""
        return [
            {
                'id': str(uuid4()),
                'date': '2024-01-15',
                'description': 'Grocery Store',
                'amount': 100.0,
                'transaction_type': 'expense',
                'category_name': 'Food'
            },
            {
                'id': str(uuid4()),
                'date': '2024-01-01',
                'description': 'Salary',
                'amount': 3000.0,
                'transaction_type': 'income',
                'category_name': 'Income'
            }
        ]

    def test_export_expense_summary_csv(self, export_service, sample_expense_summary):
        """Test CSV export of expense summary."""
        content, filename, content_type = export_service.export_expense_summary(
            sample_expense_summary, ExportFormat.CSV
        )
        
        assert content_type == "text/csv"
        assert filename.endswith('.csv')
        assert b'Expense Summary' in content
        assert b'Total Expenses,1000.0' in content
        assert b'Food,500.0,10,50.00%' in content

    def test_export_expense_summary_json(self, export_service, sample_expense_summary):
        """Test JSON export of expense summary."""
        content, filename, content_type = export_service.export_expense_summary(
            sample_expense_summary, ExportFormat.JSON
        )
        
        assert content_type == "application/json"
        assert filename.endswith('.json')
        
        # Parse JSON to verify structure
        import json
        data = json.loads(content.decode('utf-8'))
        assert data['total_expenses'] == '1000.00'
        assert len(data['categories']) == 3
        assert data['categories'][0]['category_name'] == 'Food'

    @patch('app.services.export.PANDAS_AVAILABLE', True)
    @patch('pandas.ExcelWriter')
    @patch('pandas.DataFrame')
    def test_export_expense_summary_excel(self, mock_dataframe, mock_excel_writer, export_service, sample_expense_summary):
        """Test Excel export of expense summary."""
        # Mock pandas components
        mock_writer_instance = Mock()
        mock_excel_writer.return_value.__enter__.return_value = mock_writer_instance
        mock_df_instance = Mock()
        mock_dataframe.return_value = mock_df_instance
        
        content, filename, content_type = export_service.export_expense_summary(
            sample_expense_summary, ExportFormat.EXCEL
        )
        
        assert content_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        assert filename.endswith('.xlsx')
        
        # Verify pandas methods were called
        mock_excel_writer.assert_called_once()
        mock_dataframe.assert_called()
        mock_df_instance.to_excel.assert_called()

    @patch('app.services.export.PANDAS_AVAILABLE', False)
    def test_export_expense_summary_excel_no_pandas(self, export_service, sample_expense_summary):
        """Test Excel export fails gracefully without pandas."""
        with pytest.raises(ImportError, match="pandas is required for Excel export"):
            export_service.export_expense_summary(sample_expense_summary, ExportFormat.EXCEL)

    @patch('app.services.export.REPORTLAB_AVAILABLE', True)
    @patch('app.services.export.SimpleDocTemplate')
    def test_export_expense_summary_pdf(self, mock_doc, export_service, sample_expense_summary):
        """Test PDF export of expense summary."""
        # Mock reportlab components
        mock_doc_instance = Mock()
        mock_doc.return_value = mock_doc_instance
        
        content, filename, content_type = export_service.export_expense_summary(
            sample_expense_summary, ExportFormat.PDF
        )
        
        assert content_type == "application/pdf"
        assert filename.endswith('.pdf')
        
        # Verify reportlab methods were called
        mock_doc.assert_called_once()
        mock_doc_instance.build.assert_called_once()

    @patch('app.services.export.REPORTLAB_AVAILABLE', False)
    def test_export_expense_summary_pdf_no_reportlab(self, export_service, sample_expense_summary):
        """Test PDF export fails gracefully without reportlab."""
        with pytest.raises(ImportError, match="reportlab is required for PDF export"):
            export_service.export_expense_summary(sample_expense_summary, ExportFormat.PDF)

    def test_export_financial_metrics_csv(self, export_service, sample_financial_metrics):
        """Test CSV export of financial metrics."""
        content, filename, content_type = export_service.export_financial_metrics(
            sample_financial_metrics, ExportFormat.CSV
        )
        
        assert content_type == "text/csv"
        assert filename.endswith('.csv')
        assert b'Financial Metrics' in content
        assert b'Total Balance,5000.0' in content
        assert b'Savings Rate,72.60%' in content

    def test_export_transactions_csv(self, export_service, sample_transactions):
        """Test CSV export of transactions."""
        content, filename, content_type = export_service.export_transactions(
            sample_transactions, ExportFormat.CSV
        )
        
        assert content_type == "text/csv"
        assert filename.endswith('.csv')
        assert b'Grocery Store' in content
        assert b'Salary' in content

    def test_export_transactions_empty_list(self, export_service):
        """Test CSV export with empty transaction list."""
        content, filename, content_type = export_service.export_transactions(
            [], ExportFormat.CSV
        )
        
        assert content_type == "text/csv"
        assert filename.endswith('.csv')
        assert content == b''  # Empty CSV

    def test_unsupported_export_format(self, export_service, sample_expense_summary):
        """Test error handling for unsupported export format."""
        with pytest.raises(ValueError, match="Unsupported export format"):
            export_service.export_expense_summary(sample_expense_summary, 'unsupported')

    def test_filename_generation(self, export_service, sample_expense_summary):
        """Test that filenames include timestamps."""
        content1, filename1, _ = export_service.export_expense_summary(
            sample_expense_summary, ExportFormat.CSV, "test_prefix"
        )
        
        # Wait a moment and generate another file
        import time
        time.sleep(0.01)
        
        content2, filename2, _ = export_service.export_expense_summary(
            sample_expense_summary, ExportFormat.CSV, "test_prefix"
        )
        
        # Filenames should be different due to timestamp
        assert filename1 != filename2
        assert filename1.startswith("test_prefix_")
        assert filename2.startswith("test_prefix_")

    @patch('app.services.export.PANDAS_AVAILABLE', True)
    @patch('pandas.ExcelWriter')
    @patch('pandas.DataFrame')
    def test_export_metrics_excel_with_trends(self, mock_dataframe, mock_excel_writer, export_service, sample_financial_metrics):
        """Test Excel export of financial metrics with trend data."""
        # Mock pandas components
        mock_writer_instance = Mock()
        mock_excel_writer.return_value.__enter__.return_value = mock_writer_instance
        mock_df_instance = Mock()
        mock_dataframe.return_value = mock_df_instance
        
        content, filename, content_type = export_service.export_financial_metrics(
            sample_financial_metrics, ExportFormat.EXCEL
        )
        
        assert content_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        
        # Verify that both metrics and trends sheets were created
        assert mock_df_instance.to_excel.call_count == 2  # Metrics + Trends sheets

    def test_export_json_with_pydantic_model(self, export_service, sample_expense_summary):
        """Test JSON export with Pydantic model."""
        content, filename, content_type = export_service._export_json(
            sample_expense_summary, "test.json"
        )
        
        assert content_type == "application/json"
        
        # Parse and verify JSON structure
        import json
        data = json.loads(content.decode('utf-8'))
        assert 'total_expenses' in data
        assert 'categories' in data

    def test_export_json_with_regular_data(self, export_service):
        """Test JSON export with regular dictionary data."""
        test_data = {'key': 'value', 'number': 42}
        
        content, filename, content_type = export_service._export_json(
            test_data, "test.json"
        )
        
        assert content_type == "application/json"
        
        # Parse and verify JSON
        import json
        data = json.loads(content.decode('utf-8'))
        assert data == test_data

    @patch('app.services.export.REPORTLAB_AVAILABLE', True)
    @patch('app.services.export.SimpleDocTemplate')
    def test_export_transactions_pdf_long_description(self, mock_doc, export_service):
        """Test PDF export truncates long transaction descriptions."""
        # Mock reportlab components
        mock_doc_instance = Mock()
        mock_doc.return_value = mock_doc_instance
        
        long_description_transaction = [{
            'id': str(uuid4()),
            'date': '2024-01-15',
            'description': 'This is a very long transaction description that should be truncated',
            'amount': 100.0,
            'transaction_type': 'expense',
            'category_name': 'Food'
        }]
        
        content, filename, content_type = export_service.export_transactions(
            long_description_transaction, ExportFormat.PDF
        )
        
        assert content_type == "application/pdf"
        mock_doc_instance.build.assert_called_once()

    def test_csv_export_special_characters(self, export_service):
        """Test CSV export handles special characters correctly."""
        special_transactions = [{
            'id': str(uuid4()),
            'date': '2024-01-15',
            'description': 'Transaction with "quotes" and, commas',
            'amount': 100.0,
            'transaction_type': 'expense',
            'category_name': 'Food & Dining'
        }]
        
        content, filename, content_type = export_service.export_transactions(
            special_transactions, ExportFormat.CSV
        )
        
        assert content_type == "text/csv"
        # CSV should handle special characters properly
        csv_content = content.decode('utf-8')
        assert 'Food & Dining' in csv_content