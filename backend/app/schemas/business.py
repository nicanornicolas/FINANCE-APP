"""
Business Pydantic schemas for API request/response models
"""
from pydantic import BaseModel, EmailStr, validator
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from ..models.business import BusinessType, InvoiceStatus, PaymentTerms


# Business Entity Schemas
class BusinessEntityBase(BaseModel):
    name: str
    business_type: BusinessType
    registration_number: Optional[str] = None
    tax_id: Optional[str] = None
    kra_pin: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state_province: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    default_currency: str = "KES"
    fiscal_year_start: int = 1
    is_active: bool = True

    @validator('fiscal_year_start')
    def validate_fiscal_year_start(cls, v):
        if not 1 <= v <= 12:
            raise ValueError('Fiscal year start must be between 1 and 12')
        return v


class BusinessEntityCreate(BusinessEntityBase):
    pass


class BusinessEntityUpdate(BaseModel):
    name: Optional[str] = None
    business_type: Optional[BusinessType] = None
    registration_number: Optional[str] = None
    tax_id: Optional[str] = None
    kra_pin: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state_province: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    default_currency: Optional[str] = None
    fiscal_year_start: Optional[int] = None
    is_active: Optional[bool] = None

    @validator('fiscal_year_start')
    def validate_fiscal_year_start(cls, v):
        if v is not None and not 1 <= v <= 12:
            raise ValueError('Fiscal year start must be between 1 and 12')
        return v


class BusinessEntity(BusinessEntityBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Client Schemas
class ClientBase(BaseModel):
    name: str
    company_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state_province: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    tax_id: Optional[str] = None
    kra_pin: Optional[str] = None
    default_payment_terms: PaymentTerms = PaymentTerms.NET_30
    default_currency: str = "KES"
    credit_limit: Optional[Decimal] = None
    is_active: bool = True
    notes: Optional[str] = None


class ClientCreate(ClientBase):
    business_entity_id: UUID


class ClientUpdate(BaseModel):
    name: Optional[str] = None
    company_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state_province: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    tax_id: Optional[str] = None
    kra_pin: Optional[str] = None
    default_payment_terms: Optional[PaymentTerms] = None
    default_currency: Optional[str] = None
    credit_limit: Optional[Decimal] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None


class Client(ClientBase):
    id: UUID
    business_entity_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Invoice Item Schemas
class InvoiceItemBase(BaseModel):
    description: str
    quantity: Decimal = Decimal('1.0000')
    unit_price: Decimal
    product_service_code: Optional[str] = None

    @validator('quantity')
    def validate_quantity(cls, v):
        if v <= 0:
            raise ValueError('Quantity must be greater than 0')
        return v

    @validator('unit_price')
    def validate_unit_price(cls, v):
        if v < 0:
            raise ValueError('Unit price cannot be negative')
        return v


class InvoiceItemCreate(InvoiceItemBase):
    pass


class InvoiceItemUpdate(BaseModel):
    description: Optional[str] = None
    quantity: Optional[Decimal] = None
    unit_price: Optional[Decimal] = None
    product_service_code: Optional[str] = None

    @validator('quantity')
    def validate_quantity(cls, v):
        if v is not None and v <= 0:
            raise ValueError('Quantity must be greater than 0')
        return v

    @validator('unit_price')
    def validate_unit_price(cls, v):
        if v is not None and v < 0:
            raise ValueError('Unit price cannot be negative')
        return v


class InvoiceItem(InvoiceItemBase):
    id: UUID
    invoice_id: UUID
    line_total: Decimal
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Invoice Payment Schemas
class InvoicePaymentBase(BaseModel):
    payment_date: datetime
    amount: Decimal
    payment_method: Optional[str] = None
    reference_number: Optional[str] = None
    notes: Optional[str] = None

    @validator('amount')
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError('Payment amount must be greater than 0')
        return v


class InvoicePaymentCreate(InvoicePaymentBase):
    invoice_id: UUID


class InvoicePaymentUpdate(BaseModel):
    payment_date: Optional[datetime] = None
    amount: Optional[Decimal] = None
    payment_method: Optional[str] = None
    reference_number: Optional[str] = None
    notes: Optional[str] = None

    @validator('amount')
    def validate_amount(cls, v):
        if v is not None and v <= 0:
            raise ValueError('Payment amount must be greater than 0')
        return v


class InvoicePayment(InvoicePaymentBase):
    id: UUID
    invoice_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Invoice Schemas
class InvoiceBase(BaseModel):
    invoice_number: str
    invoice_date: datetime
    due_date: datetime
    tax_rate: Decimal = Decimal('0.16')  # Default 16% VAT for Kenya
    discount_amount: Decimal = Decimal('0.00')
    currency: str = "KES"
    payment_terms: PaymentTerms = PaymentTerms.NET_30
    notes: Optional[str] = None
    terms_conditions: Optional[str] = None

    @validator('tax_rate')
    def validate_tax_rate(cls, v):
        if v < 0 or v > 1:
            raise ValueError('Tax rate must be between 0 and 1')
        return v

    @validator('discount_amount')
    def validate_discount_amount(cls, v):
        if v < 0:
            raise ValueError('Discount amount cannot be negative')
        return v


class InvoiceCreate(InvoiceBase):
    business_entity_id: UUID
    client_id: UUID
    items: List[InvoiceItemCreate]


class InvoiceUpdate(BaseModel):
    invoice_number: Optional[str] = None
    invoice_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    tax_rate: Optional[Decimal] = None
    discount_amount: Optional[Decimal] = None
    currency: Optional[str] = None
    status: Optional[InvoiceStatus] = None
    payment_terms: Optional[PaymentTerms] = None
    notes: Optional[str] = None
    terms_conditions: Optional[str] = None

    @validator('tax_rate')
    def validate_tax_rate(cls, v):
        if v is not None and (v < 0 or v > 1):
            raise ValueError('Tax rate must be between 0 and 1')
        return v

    @validator('discount_amount')
    def validate_discount_amount(cls, v):
        if v is not None and v < 0:
            raise ValueError('Discount amount cannot be negative')
        return v


class Invoice(InvoiceBase):
    id: UUID
    business_entity_id: UUID
    client_id: UUID
    subtotal: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    paid_amount: Decimal
    status: InvoiceStatus
    sent_date: Optional[datetime] = None
    viewed_date: Optional[datetime] = None
    paid_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    # Related objects
    client: Client
    invoice_items: List[InvoiceItem] = []
    payments: List[InvoicePayment] = []

    class Config:
        from_attributes = True


# Business Account Schemas
class BusinessAccountBase(BaseModel):
    is_primary: bool = False
    account_purpose: Optional[str] = None


class BusinessAccountCreate(BusinessAccountBase):
    business_entity_id: UUID
    account_id: UUID


class BusinessAccountUpdate(BaseModel):
    is_primary: Optional[bool] = None
    account_purpose: Optional[str] = None


class BusinessAccount(BusinessAccountBase):
    id: UUID
    business_entity_id: UUID
    account_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Business Expense Category Schemas
class BusinessExpenseCategoryBase(BaseModel):
    is_tax_deductible: bool = True
    tax_form_line: Optional[str] = None
    expense_type: Optional[str] = None


class BusinessExpenseCategoryCreate(BusinessExpenseCategoryBase):
    business_entity_id: UUID
    category_id: UUID


class BusinessExpenseCategoryUpdate(BaseModel):
    is_tax_deductible: Optional[bool] = None
    tax_form_line: Optional[str] = None
    expense_type: Optional[str] = None


class BusinessExpenseCategory(BusinessExpenseCategoryBase):
    id: UUID
    business_entity_id: UUID
    category_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Business Summary Schemas
class BusinessSummary(BaseModel):
    """Summary statistics for a business entity"""
    total_revenue: Decimal
    total_expenses: Decimal
    net_profit: Decimal
    outstanding_invoices: int
    overdue_invoices: int
    total_outstanding_amount: Decimal
    active_clients: int


class ProfitLossReport(BaseModel):
    """Profit and Loss report data"""
    business_entity_id: UUID
    period_start: datetime
    period_end: datetime
    revenue: Decimal
    cost_of_goods_sold: Decimal
    gross_profit: Decimal
    operating_expenses: Decimal
    net_profit: Decimal
    expense_breakdown: dict  # Category-wise expense breakdown


class CashFlowReport(BaseModel):
    """Cash Flow report data"""
    business_entity_id: UUID
    period_start: datetime
    period_end: datetime
    opening_balance: Decimal
    cash_inflows: Decimal
    cash_outflows: Decimal
    closing_balance: Decimal
    monthly_breakdown: List[dict]  # Month-wise cash flow data