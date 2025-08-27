import pytest
from decimal import Decimal
from datetime import date, datetime
from uuid import uuid4

from app.models.user import User
from app.models.account import Account, AccountType
from app.models.category import Category
from app.models.transaction import Transaction, TransactionType
from app.crud import user as crud_user
from app.crud import account as crud_account
from app.crud import category as crud_category
from app.crud import transaction as crud_transaction
from app.schemas.user import UserCreate
from app.schemas.account import AccountCreate
from app.schemas.category import CategoryCreate
from app.schemas.transaction import TransactionCreate


class TestUserModel:
    def test_create_user(self, db_session):
        """Test creating a user"""
        user_data = UserCreate(
            email="test@example.com",
            password="testpassword123",
            first_name="Test",
            last_name="User"
        )
        
        user = crud_user.user.create(db_session, obj_in=user_data)
        
        assert user.email == "test@example.com"
        assert user.first_name == "Test"
        assert user.last_name == "User"
        assert user.is_active is True
        assert user.password_hash != "testpassword123"  # Should be hashed
        assert user.id is not None
        assert user.created_at is not None

    def test_authenticate_user(self, db_session):
        """Test user authentication"""
        user_data = UserCreate(
            email="auth@example.com",
            password="testpassword123",
            first_name="Auth",
            last_name="User"
        )
        
        user = crud_user.user.create(db_session, obj_in=user_data)
        
        # Test correct credentials
        authenticated_user = crud_user.user.authenticate(
            db_session, email="auth@example.com", password="testpassword123"
        )
        assert authenticated_user is not None
        assert authenticated_user.id == user.id
        
        # Test incorrect password
        wrong_auth = crud_user.user.authenticate(
            db_session, email="auth@example.com", password="wrongpassword"
        )
        assert wrong_auth is None
        
        # Test non-existent user
        no_user = crud_user.user.authenticate(
            db_session, email="nonexistent@example.com", password="testpassword123"
        )
        assert no_user is None


class TestAccountModel:
    def test_create_account(self, db_session):
        """Test creating an account"""
        # First create a user
        user_data = UserCreate(
            email="account@example.com",
            password="testpassword123",
            first_name="Account",
            last_name="User"
        )
        user = crud_user.user.create(db_session, obj_in=user_data)
        
        # Create account
        account_data = AccountCreate(
            name="Test Checking",
            account_type=AccountType.CHECKING,
            institution="Test Bank",
            account_number="1234567890"
        )
        
        account = crud_account.account.create_with_user(
            db_session, obj_in=account_data, user_id=user.id
        )
        
        assert account.name == "Test Checking"
        assert account.account_type == AccountType.CHECKING
        assert account.institution == "Test Bank"
        assert account.user_id == user.id
        assert account.balance == Decimal("0.00")
        assert account.currency == "USD"
        assert account.is_active is True

    def test_get_accounts_by_user(self, db_session):
        """Test getting accounts by user"""
        # Create user
        user_data = UserCreate(
            email="multiaccounts@example.com",
            password="testpassword123",
            first_name="Multi",
            last_name="Accounts"
        )
        user = crud_user.user.create(db_session, obj_in=user_data)
        
        # Create multiple accounts
        account1_data = AccountCreate(
            name="Checking",
            account_type=AccountType.CHECKING
        )
        account2_data = AccountCreate(
            name="Savings",
            account_type=AccountType.SAVINGS
        )
        
        account1 = crud_account.account.create_with_user(
            db_session, obj_in=account1_data, user_id=user.id
        )
        account2 = crud_account.account.create_with_user(
            db_session, obj_in=account2_data, user_id=user.id
        )
        
        # Get accounts by user
        accounts = crud_account.account.get_by_user(db_session, user_id=user.id)
        
        assert len(accounts) == 2
        account_names = [acc.name for acc in accounts]
        assert "Checking" in account_names
        assert "Savings" in account_names


class TestCategoryModel:
    def test_create_category(self, db_session):
        """Test creating a category"""
        # Create user
        user_data = UserCreate(
            email="category@example.com",
            password="testpassword123",
            first_name="Category",
            last_name="User"
        )
        user = crud_user.user.create(db_session, obj_in=user_data)
        
        # Create category
        category_data = CategoryCreate(
            name="Food & Dining",
            color="#FF6B6B",
            icon="utensils",
            is_tax_category=False
        )
        
        category = crud_category.category.create_with_user(
            db_session, obj_in=category_data, user_id=user.id
        )
        
        assert category.name == "Food & Dining"
        assert category.color == "#FF6B6B"
        assert category.icon == "utensils"
        assert category.user_id == user.id
        assert category.parent_id is None
        assert category.is_tax_category is False

    def test_create_subcategory(self, db_session):
        """Test creating a subcategory"""
        # Create user
        user_data = UserCreate(
            email="subcategory@example.com",
            password="testpassword123",
            first_name="Sub",
            last_name="Category"
        )
        user = crud_user.user.create(db_session, obj_in=user_data)
        
        # Create parent category
        parent_data = CategoryCreate(name="Transportation")
        parent = crud_category.category.create_with_user(
            db_session, obj_in=parent_data, user_id=user.id
        )
        
        # Create subcategory
        sub_data = CategoryCreate(
            name="Gas",
            parent_id=parent.id
        )
        subcategory = crud_category.category.create_with_user(
            db_session, obj_in=sub_data, user_id=user.id
        )
        
        assert subcategory.name == "Gas"
        assert subcategory.parent_id == parent.id
        assert subcategory.user_id == user.id


class TestTransactionModel:
    def test_create_transaction(self, db_session):
        """Test creating a transaction"""
        # Create user
        user_data = UserCreate(
            email="transaction@example.com",
            password="testpassword123",
            first_name="Transaction",
            last_name="User"
        )
        user = crud_user.user.create(db_session, obj_in=user_data)
        
        # Create account
        account_data = AccountCreate(
            name="Test Account",
            account_type=AccountType.CHECKING
        )
        account = crud_account.account.create_with_user(
            db_session, obj_in=account_data, user_id=user.id
        )
        
        # Create category
        category_data = CategoryCreate(name="Groceries")
        category = crud_category.category.create_with_user(
            db_session, obj_in=category_data, user_id=user.id
        )
        
        # Create transaction
        transaction_data = TransactionCreate(
            account_id=account.id,
            date=date.today(),
            description="Grocery Store Purchase",
            amount=Decimal("45.67"),
            transaction_type=TransactionType.EXPENSE,
            category_id=category.id,
            tags=["groceries", "food"],
            is_tax_deductible=False
        )
        
        transaction = crud_transaction.transaction.create(
            db_session, obj_in=transaction_data
        )
        
        assert transaction.description == "Grocery Store Purchase"
        assert transaction.amount == Decimal("45.67")
        assert transaction.transaction_type == TransactionType.EXPENSE
        assert transaction.account_id == account.id
        assert transaction.category_id == category.id
        assert transaction.tags == ["groceries", "food"]
        assert transaction.is_tax_deductible is False
        assert transaction.confidence_score == 0.0

    def test_get_transactions_by_account(self, db_session):
        """Test getting transactions by account"""
        # Create user and account
        user_data = UserCreate(
            email="txnbyaccount@example.com",
            password="testpassword123",
            first_name="Txn",
            last_name="User"
        )
        user = crud_user.user.create(db_session, obj_in=user_data)
        
        account_data = AccountCreate(
            name="Test Account",
            account_type=AccountType.CHECKING
        )
        account = crud_account.account.create_with_user(
            db_session, obj_in=account_data, user_id=user.id
        )
        
        # Create multiple transactions
        for i in range(3):
            transaction_data = TransactionCreate(
                account_id=account.id,
                date=date.today(),
                description=f"Transaction {i+1}",
                amount=Decimal(f"{10 + i}.00"),
                transaction_type=TransactionType.EXPENSE
            )
            crud_transaction.transaction.create(db_session, obj_in=transaction_data)
        
        # Get transactions by account
        transactions = crud_transaction.transaction.get_by_account(
            db_session, account_id=account.id
        )
        
        assert len(transactions) == 3
        # Should be ordered by date descending
        descriptions = [txn.description for txn in transactions]
        assert "Transaction 1" in descriptions
        assert "Transaction 2" in descriptions
        assert "Transaction 3" in descriptions