import csv
import io
from typing import List, Dict, Tuple, Optional
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from uuid import UUID

from ..schemas.transaction import TransactionCreate
from ..models.transaction import TransactionType


class CSVImportError(Exception):
    """Custom exception for CSV import errors"""
    pass


class CSVImporter:
    """Service for importing transactions from CSV files"""
    
    # Common CSV column mappings for different bank formats
    COLUMN_MAPPINGS = {
        # Standard format
        'date': ['date', 'transaction_date', 'posted_date', 'Date'],
        'description': ['description', 'memo', 'payee', 'Description', 'Memo'],
        'amount': ['amount', 'Amount'],
        'debit': ['debit', 'withdrawal', 'Debit', 'Withdrawal'],
        'credit': ['credit', 'deposit', 'Credit', 'Deposit'],
        'balance': ['balance', 'Balance'],
        'reference': ['reference', 'check_number', 'ref', 'Reference', 'Check Number'],
        'category': ['category', 'Category'],
    }
    
    DATE_FORMATS = [
        '%Y-%m-%d',      # 2024-01-15
        '%m/%d/%Y',      # 01/15/2024
        '%d/%m/%Y',      # 15/01/2024
        '%m-%d-%Y',      # 01-15-2024
        '%d-%m-%Y',      # 15-01-2024
        '%Y/%m/%d',      # 2024/01/15
        '%m/%d/%y',      # 01/15/24
        '%d/%m/%y',      # 15/01/24
    ]

    def __init__(self, account_id: UUID):
        self.account_id = account_id
        self.errors = []
        self.duplicates = []
        self.imported = []

    def parse_csv_content(self, content: bytes, filename: str = None) -> List[TransactionCreate]:
        """Parse CSV content and return list of TransactionCreate objects"""
        try:
            # Decode content
            text_content = content.decode('utf-8-sig')  # Handle BOM
        except UnicodeDecodeError:
            try:
                text_content = content.decode('latin-1')
            except UnicodeDecodeError:
                raise CSVImportError("Unable to decode file. Please ensure it's a valid CSV file.")

        # Parse CSV
        csv_reader = csv.DictReader(io.StringIO(text_content))
        
        if not csv_reader.fieldnames:
            raise CSVImportError("CSV file appears to be empty or invalid")

        # Detect column mappings
        column_mapping = self._detect_columns(csv_reader.fieldnames)
        
        transactions = []
        row_number = 1  # Start from 1 (header is row 0)
        
        for row in csv_reader:
            row_number += 1
            try:
                transaction = self._parse_row(row, column_mapping, row_number)
                if transaction:
                    transactions.append(transaction)
            except Exception as e:
                self.errors.append(f"Row {row_number}: {str(e)}")
                continue

        return transactions

    def _detect_columns(self, fieldnames: List[str]) -> Dict[str, str]:
        """Detect which columns map to our transaction fields"""
        mapping = {}
        
        for field, possible_names in self.COLUMN_MAPPINGS.items():
            for fieldname in fieldnames:
                if fieldname.lower().strip() in [name.lower() for name in possible_names]:
                    mapping[field] = fieldname
                    break
        
        # Validate required fields
        if 'date' not in mapping:
            raise CSVImportError("Could not find date column. Expected one of: " + 
                               ", ".join(self.COLUMN_MAPPINGS['date']))
        
        if 'description' not in mapping:
            raise CSVImportError("Could not find description column. Expected one of: " + 
                               ", ".join(self.COLUMN_MAPPINGS['description']))
        
        # Must have either 'amount' or both 'debit' and 'credit'
        if 'amount' not in mapping and ('debit' not in mapping or 'credit' not in mapping):
            raise CSVImportError("Could not find amount columns. Expected either 'amount' or both 'debit' and 'credit'")
        
        return mapping

    def _parse_row(self, row: Dict[str, str], mapping: Dict[str, str], row_number: int) -> Optional[TransactionCreate]:
        """Parse a single CSV row into a TransactionCreate object"""
        # Skip empty rows
        if not any(value.strip() for value in row.values() if value):
            return None

        # Parse date
        date_str = row.get(mapping['date'], '').strip()
        if not date_str:
            raise ValueError("Date is required")
        
        transaction_date = self._parse_date(date_str)
        
        # Parse description
        description = row.get(mapping['description'], '').strip()
        if not description:
            raise ValueError("Description is required")
        
        # Parse amount
        amount, transaction_type = self._parse_amount(row, mapping)
        
        # Parse optional fields
        reference_number = row.get(mapping.get('reference', ''), '').strip() or None
        
        # Create transaction
        return TransactionCreate(
            account_id=self.account_id,
            date=transaction_date,
            description=description,
            amount=amount,
            transaction_type=transaction_type,
            reference_number=reference_number,
            tags=[],  # Could be enhanced to parse tags from description
            is_tax_deductible=False,  # Default to False, can be updated later
            notes=None
        )

    def _parse_date(self, date_str: str) -> date:
        """Parse date string using various formats"""
        for date_format in self.DATE_FORMATS:
            try:
                return datetime.strptime(date_str, date_format).date()
            except ValueError:
                continue
        
        raise ValueError(f"Could not parse date: {date_str}")

    def _parse_amount(self, row: Dict[str, str], mapping: Dict[str, str]) -> Tuple[Decimal, TransactionType]:
        """Parse amount and determine transaction type"""
        if 'amount' in mapping:
            # Single amount column
            amount_str = row.get(mapping['amount'], '').strip()
            if not amount_str:
                raise ValueError("Amount is required")
            
            amount = self._parse_decimal(amount_str)
            
            # Determine type based on sign
            if amount < 0:
                return abs(amount), TransactionType.expense
            else:
                return amount, TransactionType.income
        
        else:
            # Separate debit/credit columns
            debit_str = row.get(mapping.get('debit', ''), '').strip()
            credit_str = row.get(mapping.get('credit', ''), '').strip()
            
            if debit_str and credit_str:
                raise ValueError("Transaction cannot have both debit and credit amounts")
            
            if debit_str:
                amount = self._parse_decimal(debit_str)
                return amount, TransactionType.expense
            elif credit_str:
                amount = self._parse_decimal(credit_str)
                return amount, TransactionType.income
            else:
                raise ValueError("Either debit or credit amount is required")

    def _parse_decimal(self, amount_str: str) -> Decimal:
        """Parse decimal amount from string"""
        # Clean up the amount string
        amount_str = amount_str.replace('$', '').replace(',', '').replace('(', '-').replace(')', '').strip()
        
        try:
            return Decimal(amount_str)
        except (InvalidOperation, ValueError):
            raise ValueError(f"Invalid amount: {amount_str}")

    def check_duplicates(self, transactions: List[TransactionCreate], existing_transactions: List) -> List[TransactionCreate]:
        """Check for duplicate transactions and filter them out"""
        unique_transactions = []
        
        # Create a set of existing transaction signatures for quick lookup
        existing_signatures = set()
        for existing in existing_transactions:
            signature = self._create_transaction_signature(
                existing.date, existing.description, existing.amount
            )
            existing_signatures.add(signature)
        
        for transaction in transactions:
            signature = self._create_transaction_signature(
                transaction.date, transaction.description, transaction.amount
            )
            
            if signature in existing_signatures:
                self.duplicates.append(f"Duplicate: {transaction.description} on {transaction.date}")
            else:
                unique_transactions.append(transaction)
                existing_signatures.add(signature)  # Prevent duplicates within the import
        
        return unique_transactions

    def _create_transaction_signature(self, date: date, description: str, amount: Decimal) -> str:
        """Create a unique signature for duplicate detection"""
        return f"{date}|{description.lower().strip()}|{amount}"

    def get_import_summary(self) -> Dict[str, any]:
        """Get summary of import results"""
        return {
            "imported": len(self.imported),
            "duplicates": len(self.duplicates),
            "errors": self.errors
        }


def import_transactions_from_csv(
    content: bytes,
    account_id: UUID,
    filename: str = None,
    existing_transactions: List = None
) -> Tuple[List[TransactionCreate], Dict[str, any]]:
    """
    Import transactions from CSV content
    
    Returns:
        Tuple of (transactions_to_create, import_summary)
    """
    importer = CSVImporter(account_id)
    
    try:
        # Parse CSV content
        transactions = importer.parse_csv_content(content, filename)
        
        # Check for duplicates if existing transactions provided
        if existing_transactions:
            transactions = importer.check_duplicates(transactions, existing_transactions)
        
        importer.imported = transactions
        
        return transactions, importer.get_import_summary()
        
    except CSVImportError as e:
        importer.errors.append(str(e))
        return [], importer.get_import_summary()
    except Exception as e:
        importer.errors.append(f"Unexpected error: {str(e)}")
        return [], importer.get_import_summary()