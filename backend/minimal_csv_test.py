#!/usr/bin/env python3
"""
Minimal test for CSV parsing logic without dependencies
"""
import csv
import io
from datetime import datetime, date
from decimal import Decimal
from enum import Enum

class TransactionType(str, Enum):
    income = "income"
    expense = "expense"
    transfer = "transfer"

def parse_date(date_str: str) -> date:
    """Parse date string using various formats"""
    date_formats = [
        '%Y-%m-%d',      # 2024-01-15
        '%m/%d/%Y',      # 01/15/2024
        '%d/%m/%Y',      # 15/01/2024
        '%m-%d-%Y',      # 01-15-2024
        '%d-%m-%Y',      # 15-01-2024
        '%Y/%m/%d',      # 2024/01/15
        '%m/%d/%y',      # 01/15/24
        '%d/%m/%y',      # 15/01/24
    ]
    
    for date_format in date_formats:
        try:
            return datetime.strptime(date_str, date_format).date()
        except ValueError:
            continue
    
    raise ValueError(f"Could not parse date: {date_str}")

def parse_decimal(amount_str: str) -> Decimal:
    """Parse decimal amount from string"""
    # Clean up the amount string
    amount_str = amount_str.replace('$', '').replace(',', '').replace('(', '-').replace(')', '').strip()
    
    try:
        return Decimal(amount_str)
    except (Exception,):
        raise ValueError(f"Invalid amount: {amount_str}")

def parse_amount(amount_str: str):
    """Parse amount and determine transaction type"""
    amount = parse_decimal(amount_str)
    
    # Determine type based on sign
    if amount < 0:
        return abs(amount), TransactionType.expense
    else:
        return amount, TransactionType.income

def test_csv_parsing():
    """Test CSV parsing functionality"""
    
    # Sample CSV content
    csv_content = """Date,Description,Amount,Reference
2024-01-15,Coffee Shop Purchase,-4.50,
2024-01-16,Salary Deposit,2500.00,DD001
2024-01-17,Gas Station,-45.00,
2024-01-18,Online Purchase,-29.99,ORD123
2024-01-19,Restaurant,-35.50,"""
    
    print("Testing CSV parsing...")
    print("\nCSV Content:")
    print(csv_content)
    
    # Parse CSV
    csv_reader = csv.DictReader(io.StringIO(csv_content))
    transactions = []
    
    for row_number, row in enumerate(csv_reader, 1):
        try:
            # Parse fields
            transaction_date = parse_date(row['Date'].strip())
            description = row['Description'].strip()
            amount, transaction_type = parse_amount(row['Amount'].strip())
            reference = row.get('Reference', '').strip() or None
            
            transaction = {
                'date': transaction_date,
                'description': description,
                'amount': amount,
                'transaction_type': transaction_type,
                'reference_number': reference
            }
            
            transactions.append(transaction)
            
        except Exception as e:
            print(f"Error parsing row {row_number}: {e}")
    
    print(f"\nParsed {len(transactions)} transactions:")
    for i, transaction in enumerate(transactions, 1):
        print(f"{i}. {transaction['date']} - {transaction['description']}")
        print(f"   Amount: ${transaction['amount']} ({transaction['transaction_type'].value})")
        if transaction['reference_number']:
            print(f"   Reference: {transaction['reference_number']}")
        print()
    
    # Test specific cases
    print("Testing specific parsing cases...")
    
    # Test different date formats
    test_dates = [
        "2024-01-15",
        "01/15/2024", 
        "15/01/2024",
        "01-15-2024"
    ]
    
    for date_str in test_dates:
        try:
            parsed_date = parse_date(date_str)
            print(f"✅ {date_str} -> {parsed_date}")
        except Exception as e:
            print(f"❌ {date_str} -> {e}")
    
    # Test different amount formats
    test_amounts = [
        "-4.50",
        "$2,500.00",
        "($10.00)",
        "45.00"
    ]
    
    print("\nTesting amount parsing:")
    for amount_str in test_amounts:
        try:
            amount, tx_type = parse_amount(amount_str)
            print(f"✅ {amount_str} -> ${amount} ({tx_type.value})")
        except Exception as e:
            print(f"❌ {amount_str} -> {e}")
    
    print("\n✅ CSV parsing test completed!")

if __name__ == "__main__":
    test_csv_parsing()