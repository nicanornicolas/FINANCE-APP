import pytest
from datetime import date
from decimal import Decimal
from uuid import uuid4

from app.services.csv_importer import CSVImporter, import_transactions_from_csv, CSVImportError
from app.models.transaction import TransactionType


class TestCSVImporter:
    def test_parse_standard_csv(self):
        """Test parsing a standard CSV format"""
        csv_content = """Date,Description,Amount
2024-01-15,Coffee Shop,-4.50
2024-01-16,Salary,2500.00
2024-01-17,Gas Station,-45.00"""
        
        account_id = uuid4()
        importer = CSVImporter(account_id)
        
        transactions = importer.parse_csv_content(csv_content.encode('utf-8'))
        
        assert len(transactions) == 3
        
        # Check first transaction (expense)
        assert transactions[0].date == date(2024, 1, 15)
        assert transactions[0].description == "Coffee Shop"
        assert transactions[0].amount == Decimal("4.50")
        assert transactions[0].transaction_type == TransactionType.expense
        assert transactions[0].account_id == account_id
        
        # Check second transaction (income)
        assert transactions[1].date == date(2024, 1, 16)
        assert transactions[1].description == "Salary"
        assert transactions[1].amount == Decimal("2500.00")
        assert transactions[1].transaction_type == TransactionType.income
        
        # Check third transaction (expense)
        assert transactions[2].date == date(2024, 1, 17)
        assert transactions[2].description == "Gas Station"
        assert transactions[2].amount == Decimal("45.00")
        assert transactions[2].transaction_type == TransactionType.expense

    def test_parse_debit_credit_csv(self):
        """Test parsing CSV with separate debit/credit columns"""
        csv_content = """Date,Description,Debit,Credit
2024-01-15,Coffee Shop,4.50,
2024-01-16,Salary,,2500.00
2024-01-17,Gas Station,45.00,"""
        
        account_id = uuid4()
        importer = CSVImporter(account_id)
        
        transactions = importer.parse_csv_content(csv_content.encode('utf-8'))
        
        assert len(transactions) == 3
        assert transactions[0].transaction_type == TransactionType.expense
        assert transactions[1].transaction_type == TransactionType.income
        assert transactions[2].transaction_type == TransactionType.expense

    def test_parse_different_date_formats(self):
        """Test parsing various date formats"""
        csv_content = """Date,Description,Amount
01/15/2024,Transaction 1,-10.00
15/01/2024,Transaction 2,-20.00
2024-01-15,Transaction 3,-30.00
01-15-2024,Transaction 4,-40.00"""
        
        account_id = uuid4()
        importer = CSVImporter(account_id)
        
        transactions = importer.parse_csv_content(csv_content.encode('utf-8'))
        
        # All should parse to the same date
        expected_date = date(2024, 1, 15)
        for transaction in transactions:
            assert transaction.date == expected_date

    def test_parse_with_reference_numbers(self):
        """Test parsing CSV with reference numbers"""
        csv_content = """Date,Description,Amount,Reference
2024-01-15,Check Payment,-100.00,1001
2024-01-16,Direct Deposit,2500.00,DD123"""
        
        account_id = uuid4()
        importer = CSVImporter(account_id)
        
        transactions = importer.parse_csv_content(csv_content.encode('utf-8'))
        
        assert len(transactions) == 2
        assert transactions[0].reference_number == "1001"
        assert transactions[1].reference_number == "DD123"

    def test_parse_with_currency_symbols(self):
        """Test parsing amounts with currency symbols and formatting"""
        csv_content = """Date,Description,Amount
2024-01-15,Purchase,-$1,234.56
2024-01-16,Refund,$45.00
2024-01-17,Fee,($10.00)"""
        
        account_id = uuid4()
        importer = CSVImporter(account_id)
        
        transactions = importer.parse_csv_content(csv_content.encode('utf-8'))
        
        assert len(transactions) == 3
        assert transactions[0].amount == Decimal("1234.56")
        assert transactions[1].amount == Decimal("45.00")
        assert transactions[2].amount == Decimal("10.00")
        assert transactions[2].transaction_type == TransactionType.expense  # Parentheses indicate negative

    def test_skip_empty_rows(self):
        """Test that empty rows are skipped"""
        csv_content = """Date,Description,Amount
2024-01-15,Valid Transaction,-10.00

2024-01-16,Another Valid Transaction,20.00
,,"""
        
        account_id = uuid4()
        importer = CSVImporter(account_id)
        
        transactions = importer.parse_csv_content(csv_content.encode('utf-8'))
        
        assert len(transactions) == 2
        assert transactions[0].description == "Valid Transaction"
        assert transactions[1].description == "Another Valid Transaction"

    def test_error_handling_missing_required_fields(self):
        """Test error handling for missing required fields"""
        csv_content = """Date,Description,Amount
,Missing Date,-10.00
2024-01-15,,-20.00
2024-01-16,Missing Amount,"""
        
        account_id = uuid4()
        importer = CSVImporter(account_id)
        
        transactions = importer.parse_csv_content(csv_content.encode('utf-8'))
        
        # Should have errors but still return valid transactions
        assert len(transactions) == 0  # All rows have errors
        assert len(importer.errors) == 3

    def test_error_handling_invalid_date(self):
        """Test error handling for invalid dates"""
        csv_content = """Date,Description,Amount
invalid-date,Transaction,-10.00
2024-01-15,Valid Transaction,-20.00"""
        
        account_id = uuid4()
        importer = CSVImporter(account_id)
        
        transactions = importer.parse_csv_content(csv_content.encode('utf-8'))
        
        assert len(transactions) == 1  # Only valid transaction
        assert len(importer.errors) == 1
        assert "Could not parse date" in importer.errors[0]

    def test_error_handling_invalid_amount(self):
        """Test error handling for invalid amounts"""
        csv_content = """Date,Description,Amount
2024-01-15,Invalid Amount,not-a-number
2024-01-16,Valid Transaction,-20.00"""
        
        account_id = uuid4()
        importer = CSVImporter(account_id)
        
        transactions = importer.parse_csv_content(csv_content.encode('utf-8'))
        
        assert len(transactions) == 1  # Only valid transaction
        assert len(importer.errors) == 1
        assert "Invalid amount" in importer.errors[0]

    def test_duplicate_detection(self):
        """Test duplicate transaction detection"""
        csv_content = """Date,Description,Amount
2024-01-15,Coffee Shop,-4.50
2024-01-16,Salary,2500.00
2024-01-15,Coffee Shop,-4.50"""  # Duplicate
        
        account_id = uuid4()
        
        # Mock existing transaction
        class MockTransaction:
            def __init__(self, date, description, amount):
                self.date = date
                self.description = description
                self.amount = amount
        
        existing_transactions = [
            MockTransaction(date(2024, 1, 15), "Coffee Shop", Decimal("4.50"))
        ]
        
        transactions, summary = import_transactions_from_csv(
            csv_content.encode('utf-8'), account_id, existing_transactions=existing_transactions
        )
        
        # Should only have the salary transaction (other two are duplicates)
        assert len(transactions) == 1
        assert transactions[0].description == "Salary"
        assert summary["duplicates"] == 2

    def test_missing_required_columns(self):
        """Test error when required columns are missing"""
        csv_content = """NotDate,NotDescription,NotAmount
2024-01-15,Transaction,-10.00"""
        
        account_id = uuid4()
        
        transactions, summary = import_transactions_from_csv(
            csv_content.encode('utf-8'), account_id
        )
        
        assert len(transactions) == 0
        assert len(summary["errors"]) > 0
        assert "Could not find date column" in summary["errors"][0]

    def test_empty_csv(self):
        """Test handling of empty CSV"""
        csv_content = ""
        
        account_id = uuid4()
        
        transactions, summary = import_transactions_from_csv(
            csv_content.encode('utf-8'), account_id
        )
        
        assert len(transactions) == 0
        assert len(summary["errors"]) > 0

    def test_case_insensitive_column_detection(self):
        """Test that column detection is case insensitive"""
        csv_content = """DATE,DESCRIPTION,AMOUNT
2024-01-15,Transaction,-10.00"""
        
        account_id = uuid4()
        importer = CSVImporter(account_id)
        
        transactions = importer.parse_csv_content(csv_content.encode('utf-8'))
        
        assert len(transactions) == 1
        assert transactions[0].description == "Transaction"