import pytest
import io
from datetime import date
from decimal import Decimal
from uuid import uuid4


def test_csv_importer_basic():
    """Test basic CSV importer functionality without full app dependencies"""
    
    # Test the _parse_decimal method directly
    from app.services.csv_importer import CSVImporter
    
    account_id = uuid4()
    importer = CSVImporter(account_id)
    
    # Test decimal parsing
    assert importer._parse_decimal("4.50") == Decimal("4.50")
    assert importer._parse_decimal("$4.50") == Decimal("4.50")
    assert importer._parse_decimal("($45.00)") == Decimal("-45.00")
    assert importer._parse_decimal("-$45.00") == Decimal("-45.00")
    
    print("Decimal parsing tests passed!")


def test_date_parsing():
    """Test date parsing functionality"""
    from app.services.csv_importer import CSVImporter
    
    account_id = uuid4()
    importer = CSVImporter(account_id)
    
    # Test various date formats
    assert importer._parse_date("2024-01-15") == date(2024, 1, 15)
    assert importer._parse_date("01/15/2024") == date(2024, 1, 15)
    assert importer._parse_date("15/01/2024") == date(2024, 1, 15)
    
    print("Date parsing tests passed!")


def test_column_detection():
    """Test column detection"""
    from app.services.csv_importer import CSVImporter
    
    account_id = uuid4()
    importer = CSVImporter(account_id)
    
    # Test standard columns
    fieldnames = ["Date", "Description", "Amount"]
    mapping = importer._detect_columns(fieldnames)
    
    assert mapping["date"] == "Date"
    assert mapping["description"] == "Description"
    assert mapping["amount"] == "Amount"
    
    print("Column detection tests passed!")


def test_transaction_type_enum():
    """Test that TransactionType enum is accessible"""
    from app.models.transaction import TransactionType
    
    assert hasattr(TransactionType, 'INCOME')
    assert hasattr(TransactionType, 'EXPENSE')
    assert hasattr(TransactionType, 'TRANSFER')
    
    print("TransactionType enum tests passed!")


def test_transaction_schema():
    """Test TransactionCreate schema"""
    from app.schemas.transaction import TransactionCreate
    from app.models.transaction import TransactionType
    
    account_id = uuid4()
    
    transaction = TransactionCreate(
        account_id=account_id,
        date=date(2024, 1, 15),
        description="Test Transaction",
        amount=Decimal("10.00"),
        transaction_type=TransactionType.EXPENSE
    )
    
    assert transaction.account_id == account_id
    assert transaction.description == "Test Transaction"
    assert transaction.amount == Decimal("10.00")
    assert transaction.transaction_type == TransactionType.EXPENSE
    
    print("TransactionCreate schema tests passed!")


def test_full_csv_parsing():
    """Test full CSV parsing functionality"""
    from app.services.csv_importer import CSVImporter
    from app.models.transaction import TransactionType

    account_id = uuid4()
    importer = CSVImporter(account_id)

    csv_content = """Date,Description,Amount
2024-01-15,Coffee Shop,-4.50
2024-01-16,Salary,2500.00
2024-01-17,Gas Station,-45.00"""

    content_bytes = csv_content.encode('utf-8')

    try:
        transactions = importer.parse_csv_content(content_bytes)
        print(f"Parsed {len(transactions)} transactions")
        print(f"Errors: {importer.errors}")

        if transactions:
            for i, t in enumerate(transactions):
                print(f"Transaction {i}: {t.date}, {t.description}, {t.amount}, {t.transaction_type}")

        assert len(transactions) == 3
        assert transactions[0].transaction_type == TransactionType.EXPENSE
        assert transactions[1].transaction_type == TransactionType.INCOME
        assert transactions[2].transaction_type == TransactionType.EXPENSE

        print("Full CSV parsing tests passed!")

    except Exception as e:
        print(f"Error in CSV parsing: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    test_csv_importer_basic()
    test_date_parsing()
    test_column_detection()
    test_transaction_type_enum()
    test_transaction_schema()
    test_full_csv_parsing()
    print("All tests passed!")
