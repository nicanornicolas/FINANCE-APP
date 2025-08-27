#!/usr/bin/env python3
"""
Simple test script to verify CSV import functionality
"""
import asyncio
from uuid import uuid4
from app.services.csv_importer import import_transactions_from_csv

async def test_csv_import():
    """Test the CSV import functionality"""
    
    # Sample CSV content
    csv_content = """Date,Description,Amount,Reference
2024-01-15,Coffee Shop Purchase,-4.50,
2024-01-16,Salary Deposit,2500.00,DD001
2024-01-17,Gas Station,-45.00,
2024-01-18,Online Purchase,-29.99,ORD123
2024-01-19,Restaurant,-35.50,"""
    
    account_id = uuid4()
    
    print("Testing CSV import...")
    print(f"Account ID: {account_id}")
    print("\nCSV Content:")
    print(csv_content)
    
    # Test import
    transactions, summary = import_transactions_from_csv(
        csv_content.encode('utf-8'), 
        account_id,
        filename="test.csv"
    )
    
    print(f"\nImport Results:")
    print(f"Transactions to create: {len(transactions)}")
    print(f"Import summary: {summary}")
    
    print("\nParsed Transactions:")
    for i, transaction in enumerate(transactions, 1):
        print(f"{i}. {transaction.date} - {transaction.description} - ${transaction.amount} ({transaction.transaction_type})")
        if transaction.reference_number:
            print(f"   Reference: {transaction.reference_number}")
    
    # Test with errors
    print("\n" + "="*50)
    print("Testing with invalid data...")
    
    invalid_csv = """Date,Description,Amount
invalid-date,Bad Transaction,-10.00
2024-01-15,Good Transaction,-20.00
2024-01-16,Bad Amount,not-a-number"""
    
    transactions, summary = import_transactions_from_csv(
        invalid_csv.encode('utf-8'), 
        account_id,
        filename="invalid.csv"
    )
    
    print(f"\nResults with errors:")
    print(f"Valid transactions: {len(transactions)}")
    print(f"Errors: {len(summary['errors'])}")
    for error in summary['errors']:
        print(f"  - {error}")

if __name__ == "__main__":
    asyncio.run(test_csv_import())