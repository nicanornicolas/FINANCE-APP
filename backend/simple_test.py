#!/usr/bin/env python3
"""
Simple standalone test for CSV import functionality
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from uuid import uuid4
from datetime import date
from decimal import Decimal

# Test the CSV importer directly
def test_csv_parsing():
    """Test CSV parsing without database dependencies"""
    
    # Import the CSV importer
    from app.services.csv_importer import CSVImporter
    from app.models.transaction import TransactionType
    
    # Sample CSV content
    csv_content = """Date,Description,Amount,Reference
2024-01-15,Coffee Shop Purchase,-4.50,
2024-01-16,Salary Deposit,2500.00,DD001
2024-01-17,Gas Station,-45.00,
2024-01-18,Online Purchase,-29.99,ORD123"""
    
    account_id = uuid4()
    importer = CSVImporter(account_id)
    
    print("Testing CSV parsing...")
    print(f"Account ID: {account_id}")
    print("\nCSV Content:")
    print(csv_content)
    
    try:
        # Parse CSV
        transactions = importer.parse_csv_content(csv_content.encode('utf-8'))
        
        print(f"\nParsed {len(transactions)} transactions:")
        for i, transaction in enumerate(transactions, 1):
            print(f"{i}. {transaction.date} - {transaction.description}")
            print(f"   Amount: ${transaction.amount} ({transaction.transaction_type.value})")
            if transaction.reference_number:
                print(f"   Reference: {transaction.reference_number}")
            print()
        
        # Verify specific transactions
        assert len(transactions) == 4
        assert transactions[0].description == "Coffee Shop Purchase"
        assert transactions[0].amount == Decimal("4.50")
        assert transactions[0].transaction_type == TransactionType.expense
        
        assert transactions[1].description == "Salary Deposit"
        assert transactions[1].amount == Decimal("2500.00")
        assert transactions[1].transaction_type == TransactionType.income
        assert transactions[1].reference_number == "DD001"
        
        print("✅ All tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_csv_parsing()