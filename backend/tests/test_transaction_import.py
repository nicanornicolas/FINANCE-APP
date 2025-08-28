import pytest
import io
from datetime import date
from decimal import Decimal
from uuid import uuid4

from app.services.csv_importer import CSVImporter, CSVImportError, import_transactions_from_csv
from app.schemas.transaction import TransactionCreate
from app.models.transaction import TransactionType


class TestCSVImporter:
    """Test CSV import functionality"""
    
    def test_parse_standard_csv_format(self):
        """Test parsing standard CSV format"""
        account_id = uuid4()
        importer = CSVImporter(account_id)
        
        csv_content = """Date,Description,Amount
2024-01-15,Coffee Shop,-4.50
2024-01-16,Salary,2500.00
2024-01-17,Gas Station,-45.00"""
        
        content_bytes = csv_content.encode('utf-8')
        transactions = importer.parse_csv_content(content_bytes)

        # Debug output
        print(f"Transactions parsed: {len(transactions)}")
        print(f"Errors: {importer.errors}")
        if transactions:
            print(f"First transaction: {transactions[0]}")

        assert len(transactions) == 3
        
        # Check first transaction (expense)
        assert transactions[0].date == date(2024, 1, 15)
        assert transactions[0].description == "Coffee Shop"
        assert transactions[0].amount == Decimal("4.50")
        assert transactions[0].transaction_type == TransactionType.EXPENSE
        assert transactions[0].account_id == account_id

        # Check second transaction (income)
        assert transactions[1].date == date(2024, 1, 16)
        assert transactions[1].description == "Salary"
        assert transactions[1].amount == Decimal("2500.00")
        assert transactions[1].transaction_type == TransactionType.INCOME

        # Check third transaction (expense)
        assert transactions[2].date == date(2024, 1, 17)
        assert transactions[2].description == "Gas Station"
        assert transactions[2].amount == Decimal("45.00")
        assert transactions[2].transaction_type == TransactionType.EXPENSE
    
    def test_parse_debit_credit_format(self):
        """Test parsing CSV with separate debit/credit columns"""
        account_id = uuid4()
        importer = CSVImporter(account_id)
        
        csv_content = """Date,Description,Debit,Credit
2024-01-15,Coffee Shop,4.50,
2024-01-16,Salary,,2500.00
2024-01-17,Gas Station,45.00,"""
        
        content_bytes = csv_content.encode('utf-8')
        transactions = importer.parse_csv_content(content_bytes)
        
        assert len(transactions) == 3
        assert transactions[0].transaction_type == TransactionType.EXPENSE
        assert transactions[1].transaction_type == TransactionType.INCOME
        assert transactions[2].transaction_type == TransactionType.EXPENSE
    
    def test_parse_different_date_formats(self):
        """Test parsing various date formats"""
        account_id = uuid4()
        importer = CSVImporter(account_id)
        
        test_cases = [
            ("2024-01-15", date(2024, 1, 15)),
            ("01/15/2024", date(2024, 1, 15)),
            ("15/01/2024", date(2024, 1, 15)),
            ("01-15-2024", date(2024, 1, 15)),
            ("2024/01/15", date(2024, 1, 15)),
            ("01/15/24", date(2024, 1, 15)),
        ]
        
        for date_str, expected_date in test_cases:
            parsed_date = importer._parse_date(date_str)
            assert parsed_date == expected_date, f"Failed to parse {date_str}"
    
    def test_parse_amount_with_currency_symbols(self):
        """Test parsing amounts with currency symbols and formatting"""
        account_id = uuid4()
        importer = CSVImporter(account_id)
        
        test_cases = [
            ("$4.50", Decimal("4.50")),
            ("$1,234.56", Decimal("1234.56")),
            ("($45.00)", Decimal("-45.00")),  # Parentheses for negative
            ("-$45.00", Decimal("-45.00")),
            ("4.50", Decimal("4.50")),
            ("1,234.56", Decimal("1234.56")),
        ]
        
        for amount_str, expected_amount in test_cases:
            parsed_amount = importer._parse_decimal(amount_str)
            assert parsed_amount == expected_amount, f"Failed to parse {amount_str}"
    
    def test_column_detection(self):
        """Test automatic column detection"""
        account_id = uuid4()
        importer = CSVImporter(account_id)
        
        # Test various column name variations
        fieldnames = ["Date", "Description", "Amount"]
        mapping = importer._detect_columns(fieldnames)
        assert mapping["date"] == "Date"
        assert mapping["description"] == "Description"
        assert mapping["amount"] == "Amount"
        
        # Test alternative names
        fieldnames = ["transaction_date", "memo", "debit", "credit"]
        mapping = importer._detect_columns(fieldnames)
        assert mapping["date"] == "transaction_date"
        assert mapping["description"] == "memo"
        assert mapping["debit"] == "debit"
        assert mapping["credit"] == "credit"
    
    def test_missing_required_columns(self):
        """Test error handling for missing required columns"""
        account_id = uuid4()
        importer = CSVImporter(account_id)
        
        # Missing date column
        with pytest.raises(CSVImportError, match="Could not find date column"):
            importer._detect_columns(["Description", "Amount"])
        
        # Missing description column
        with pytest.raises(CSVImportError, match="Could not find description column"):
            importer._detect_columns(["Date", "Amount"])
        
        # Missing amount columns
        with pytest.raises(CSVImportError, match="Could not find amount columns"):
            importer._detect_columns(["Date", "Description"])
    
    def test_duplicate_detection(self):
        """Test duplicate transaction detection"""
        account_id = uuid4()
        importer = CSVImporter(account_id)
        
        # Create some existing transactions
        class MockTransaction:
            def __init__(self, date, description, amount):
                self.date = date
                self.description = description
                self.amount = amount
        
        existing_transactions = [
            MockTransaction(date(2024, 1, 15), "Coffee Shop", Decimal("4.50")),
            MockTransaction(date(2024, 1, 16), "Gas Station", Decimal("45.00")),
        ]
        
        # Create new transactions with some duplicates
        new_transactions = [
            TransactionCreate(
                account_id=account_id,
                date=date(2024, 1, 15),
                description="Coffee Shop",
                amount=Decimal("4.50"),
                transaction_type=TransactionType.EXPENSE
            ),
            TransactionCreate(
                account_id=account_id,
                date=date(2024, 1, 17),
                description="New Transaction",
                amount=Decimal("10.00"),
                transaction_type=TransactionType.EXPENSE
            ),
        ]
        
        unique_transactions = importer.check_duplicates(new_transactions, existing_transactions)
        
        assert len(unique_transactions) == 1
        assert unique_transactions[0].description == "New Transaction"
        assert len(importer.duplicates) == 1
    
    def test_error_handling_invalid_data(self):
        """Test error handling for invalid data"""
        account_id = uuid4()
        importer = CSVImporter(account_id)
        
        csv_content = """Date,Description,Amount
invalid-date,Coffee Shop,4.50
2024-01-16,Valid Transaction,10.00
2024-01-17,Invalid Amount,invalid"""
        
        content_bytes = csv_content.encode('utf-8')
        transactions = importer.parse_csv_content(content_bytes)
        
        # Should only parse the valid transaction
        assert len(transactions) == 1
        assert transactions[0].description == "Valid Transaction"
        
        # Should have errors for invalid rows
        assert len(importer.errors) == 2
        assert "Row 2" in importer.errors[0]  # Invalid date
        assert "Row 4" in importer.errors[1]  # Invalid amount
    
    def test_empty_csv_handling(self):
        """Test handling of empty CSV files"""
        account_id = uuid4()
        importer = CSVImporter(account_id)
        
        # Empty content
        with pytest.raises(CSVImportError, match="CSV file appears to be empty"):
            importer.parse_csv_content(b"")
        
        # Only header
        csv_content = "Date,Description,Amount\n"
        content_bytes = csv_content.encode('utf-8')
        transactions = importer.parse_csv_content(content_bytes)
        assert len(transactions) == 0
    
    def test_unicode_handling(self):
        """Test handling of Unicode characters and BOM"""
        account_id = uuid4()
        importer = CSVImporter(account_id)
        
        # CSV with Unicode characters
        csv_content = """Date,Description,Amount
2024-01-15,Café Münchën,-4.50
2024-01-16,Résumé Service,25.00"""
        
        # Test with BOM
        content_bytes = csv_content.encode('utf-8-sig')
        transactions = importer.parse_csv_content(content_bytes)
        
        assert len(transactions) == 2
        assert transactions[0].description == "Café Münchën"
        assert transactions[1].description == "Résumé Service"
    
    def test_import_summary(self):
        """Test import summary generation"""
        account_id = uuid4()
        
        csv_content = """Date,Description,Amount
2024-01-15,Coffee Shop,-4.50
2024-01-16,Salary,2500.00"""
        
        content_bytes = csv_content.encode('utf-8')
        
        transactions, summary = import_transactions_from_csv(
            content_bytes, account_id, "test.csv"
        )
        
        assert summary["imported"] == 2
        assert summary["duplicates"] == 0
        assert len(summary["errors"]) == 0
        assert len(transactions) == 2


class TestCSVImportEdgeCases:
    """Test edge cases and error conditions"""
    
    def test_mixed_amount_formats_in_single_file(self):
        """Test handling mixed amount formats"""
        account_id = uuid4()
        importer = CSVImporter(account_id)
        
        csv_content = """Date,Description,Amount
2024-01-15,Transaction 1,$4.50
2024-01-16,Transaction 2,(45.00)
2024-01-17,Transaction 3,"1,234.56\""""
        
        content_bytes = csv_content.encode('utf-8')
        transactions = importer.parse_csv_content(content_bytes)
        
        assert len(transactions) == 3
        assert transactions[0].amount == Decimal("4.50")
        assert transactions[1].amount == Decimal("45.00")
        assert transactions[2].amount == Decimal("1234.56")
    
    def test_whitespace_handling(self):
        """Test handling of whitespace in CSV data"""
        account_id = uuid4()
        importer = CSVImporter(account_id)
        
        csv_content = """Date,Description,Amount
  2024-01-15  ,  Coffee Shop  ,  -4.50  
2024-01-16,Salary,2500.00"""
        
        content_bytes = csv_content.encode('utf-8')
        transactions = importer.parse_csv_content(content_bytes)
        
        assert len(transactions) == 2
        assert transactions[0].description == "Coffee Shop"  # Whitespace trimmed
        assert transactions[0].amount == Decimal("4.50")
    
    def test_case_insensitive_column_matching(self):
        """Test case-insensitive column name matching"""
        account_id = uuid4()
        importer = CSVImporter(account_id)
        
        # Mixed case column names
        fieldnames = ["DATE", "description", "Amount"]
        mapping = importer._detect_columns(fieldnames)
        
        assert mapping["date"] == "DATE"
        assert mapping["description"] == "description"
        assert mapping["amount"] == "Amount"
