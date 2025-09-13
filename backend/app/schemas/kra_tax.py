"""
KRA Tax Pydantic schemas for request/response validation
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from decimal import Decimal
from uuid import UUID
from enum import Enum


class KRAFilingType(str, Enum):
    INDIVIDUAL = "individual"
    CORPORATE = "corporate"
    VAT = "vat"
    WITHHOLDING = "withholding"
    TURNOVER = "turnover"
    RENTAL = "rental"
    CAPITAL_GAINS = "capital_gains"


class KRAFilingStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    PAID = "paid"
    OVERDUE = "overdue"


class KRATaxpayerType(str, Enum):
    INDIVIDUAL = "individual"
    CORPORATE = "corporate"
    PARTNERSHIP = "partnership"
    TRUST = "trust"


# KRA Taxpayer Schemas
class KRATaxpayerBase(BaseModel):
    kra_pin: str = Field(..., min_length=11, max_length=11, description="KRA PIN (11 characters)")
    taxpayer_name: str = Field(..., min_length=1, max_length=255)
    taxpayer_type: KRATaxpayerType
    tax_office: Optional[str] = Field(None, max_length=100)

    @validator('kra_pin')
    def validate_kra_pin(cls, v):
        if not v.startswith('P') or len(v) != 11:
            raise ValueError('KRA PIN must start with P and be 11 characters long')
        return v.upper()


class KRATaxpayerCreate(KRATaxpayerBase):
    pass


class KRATaxpayerUpdate(BaseModel):
    taxpayer_name: Optional[str] = Field(None, min_length=1, max_length=255)
    tax_office: Optional[str] = Field(None, max_length=100)


class KRATaxpayerResponse(KRATaxpayerBase):
    id: UUID
    user_id: UUID
    registration_date: Optional[datetime]
    is_verified: bool
    last_sync: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# KRA Tax Filing Schemas
class KRATaxFilingBase(BaseModel):
    tax_year: int = Field(..., ge=2000, le=2030)
    filing_type: KRAFilingType
    due_date: Optional[datetime]


class KRATaxFilingCreate(KRATaxFilingBase):
    taxpayer_id: UUID


class KRATaxFilingUpdate(BaseModel):
    forms_data: Optional[Dict[str, Any]]
    calculated_tax: Optional[Decimal]
    tax_due: Optional[Decimal]
    status: Optional[KRAFilingStatus]


class KRATaxFilingResponse(KRATaxFilingBase):
    id: UUID
    user_id: UUID
    taxpayer_id: UUID
    forms_data: Optional[Dict[str, Any]]
    calculated_tax: Optional[Decimal]
    tax_due: Optional[Decimal]
    payments_made: Decimal
    filing_date: Optional[datetime]
    kra_reference: Optional[str]
    status: KRAFilingStatus
    submission_receipt: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# KRA Tax Payment Schemas
class KRATaxPaymentBase(BaseModel):
    amount: Decimal = Field(..., gt=0)
    payment_method: Optional[str] = Field(None, max_length=50)


class KRATaxPaymentCreate(KRATaxPaymentBase):
    filing_id: UUID


class KRATaxPaymentResponse(KRATaxPaymentBase):
    id: UUID
    filing_id: UUID
    payment_reference: str
    payment_date: datetime
    kra_receipt: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# KRA Tax Deduction Schemas
class KRATaxDeductionBase(BaseModel):
    tax_year: int = Field(..., ge=2000, le=2030)
    deduction_type: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=1, max_length=255)
    amount: Decimal = Field(..., gt=0)
    supporting_documents: Optional[Dict[str, Any]]


class KRATaxDeductionCreate(KRATaxDeductionBase):
    pass


class KRATaxDeductionUpdate(BaseModel):
    description: Optional[str] = Field(None, min_length=1, max_length=255)
    amount: Optional[Decimal] = Field(None, gt=0)
    supporting_documents: Optional[Dict[str, Any]]
    is_verified: Optional[bool]


class KRATaxDeductionResponse(KRATaxDeductionBase):
    id: UUID
    user_id: UUID
    is_verified: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# KRA Tax Calculation Schemas
class KRATaxCalculationRequest(BaseModel):
    tax_year: int = Field(..., ge=2000, le=2030)
    filing_type: KRAFilingType
    income_data: Dict[str, Decimal]
    deductions: Optional[List[Dict[str, Any]]] = []


class KRATaxCalculationResponse(BaseModel):
    tax_year: int
    filing_type: KRAFilingType
    gross_income: Decimal
    taxable_income: Decimal
    total_deductions: Decimal
    calculated_tax: Decimal
    tax_brackets: List[Dict[str, Any]]
    effective_rate: float
    marginal_rate: float


# KRA PIN Validation Schemas
class KRAPINValidationRequest(BaseModel):
    kra_pin: str = Field(..., min_length=11, max_length=11)

    @validator('kra_pin')
    def validate_kra_pin(cls, v):
        if not v.startswith('P') or len(v) != 11:
            raise ValueError('KRA PIN must start with P and be 11 characters long')
        return v.upper()


class KRAPINValidationResponse(BaseModel):
    kra_pin: str
    is_valid: bool
    taxpayer_name: Optional[str]
    taxpayer_type: Optional[str]
    tax_office: Optional[str]
    registration_date: Optional[date]
    status: str


# KRA Tax Form Schemas
class KRAIndividualTaxForm(BaseModel):
    """Individual Income Tax Form (IT1)"""
    taxpayer_info: Dict[str, Any]
    employment_income: Optional[Decimal] = 0
    business_income: Optional[Decimal] = 0
    rental_income: Optional[Decimal] = 0
    investment_income: Optional[Decimal] = 0
    other_income: Optional[Decimal] = 0
    total_income: Decimal
    
    # Deductions
    insurance_relief: Optional[Decimal] = 0
    mortgage_interest: Optional[Decimal] = 0
    pension_contributions: Optional[Decimal] = 0
    other_deductions: Optional[Decimal] = 0
    total_deductions: Decimal
    
    taxable_income: Decimal
    tax_payable: Decimal
    withholding_tax: Optional[Decimal] = 0
    advance_tax: Optional[Decimal] = 0
    balance_due: Decimal


class KRAVATForm(BaseModel):
    """VAT Return Form (VAT 3)"""
    taxpayer_info: Dict[str, Any]
    tax_period: str
    
    # Sales
    standard_rated_sales: Optional[Decimal] = 0
    zero_rated_sales: Optional[Decimal] = 0
    exempt_sales: Optional[Decimal] = 0
    total_sales: Decimal
    output_vat: Decimal
    
    # Purchases
    standard_rated_purchases: Optional[Decimal] = 0
    zero_rated_purchases: Optional[Decimal] = 0
    exempt_purchases: Optional[Decimal] = 0
    total_purchases: Decimal
    input_vat: Decimal
    
    net_vat: Decimal
    vat_payable: Decimal


# KRA API Response Schemas
class KRAAPIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]]
    error_code: Optional[str]
    timestamp: datetime


class KRAFilingSubmissionResponse(BaseModel):
    filing_id: UUID
    kra_reference: str
    submission_date: datetime
    status: str
    receipt_url: Optional[str]
    next_steps: List[str]


# KRA Tax Amendment Schemas
class KRATaxAmendmentBase(BaseModel):
    reason: str = Field(..., min_length=10, max_length=1000)
    amended_data: Dict[str, Any]


class KRATaxAmendmentCreate(KRATaxAmendmentBase):
    original_filing_id: UUID


class KRATaxAmendmentUpdate(BaseModel):
    reason: Optional[str] = Field(None, min_length=10, max_length=1000)
    amended_data: Optional[Dict[str, Any]]
    status: Optional[str]
    processing_notes: Optional[str]


class KRATaxAmendmentResponse(KRATaxAmendmentBase):
    id: UUID
    original_filing_id: UUID
    user_id: UUID
    amendment_reference: Optional[str]
    original_data: Dict[str, Any]
    changes_summary: Optional[Dict[str, Any]]
    status: str
    submission_date: Optional[datetime]
    processing_notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# KRA Tax Document Schemas
class KRATaxDocumentBase(BaseModel):
    document_type: str = Field(..., min_length=1, max_length=50)
    filename: str = Field(..., min_length=1, max_length=255)


class KRATaxDocumentCreate(KRATaxDocumentBase):
    filing_id: Optional[UUID] = None
    file_content: bytes
    mime_type: str


class KRATaxDocumentUpdate(BaseModel):
    verification_status: Optional[str]
    metadata: Optional[Dict[str, Any]]


class KRATaxDocumentResponse(KRATaxDocumentBase):
    id: UUID
    filing_id: Optional[UUID]
    user_id: UUID
    original_filename: str
    file_path: str
    file_size: int
    mime_type: str
    kra_document_id: Optional[str]
    upload_date: datetime
    verification_status: str
    metadata: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# KRA Filing Validation Schemas
class KRAFilingValidationResponse(BaseModel):
    id: UUID
    filing_id: UUID
    validation_id: Optional[str]
    is_valid: bool
    errors: Optional[List[Dict[str, Any]]]
    warnings: Optional[List[Dict[str, Any]]]
    validation_date: datetime
    created_at: datetime

    class Config:
        from_attributes = True


# KRA Filing History Schemas
class KRAFilingHistoryItem(BaseModel):
    kra_reference: str
    tax_year: int
    filing_type: str
    status: str
    submission_date: datetime
    tax_due: Optional[Decimal]
    amount_paid: Optional[Decimal]


class KRAFilingHistoryResponse(BaseModel):
    filings: List[KRAFilingHistoryItem]
    total_count: int


# KRA Payment Schemas
class KRAPaymentInitiationRequest(BaseModel):
    filing_id: UUID
    amount: Decimal = Field(..., gt=0)
    payment_method: str
    return_url: Optional[str]


class KRAPaymentInitiationResponse(BaseModel):
    payment_reference: str
    amount: Decimal
    payment_url: str
    expires_at: datetime
    payment_methods: List[str]


class KRAPaymentConfirmationRequest(BaseModel):
    payment_reference: str
    transaction_id: str
    payment_method: str


class KRAPaymentMethodResponse(BaseModel):
    method_id: str
    name: str
    description: str
    processing_time: str
    fees: Decimal


class KRAPaymentMethodsResponse(BaseModel):
    methods: List[KRAPaymentMethodResponse]


# KRA Form Validation Schemas
class KRAFormValidationRequest(BaseModel):
    filing_type: KRAFilingType
    form_data: Dict[str, Any]
    tax_year: int


class KRAFormValidationError(BaseModel):
    field: str
    message: str
    error_code: Optional[str]


class KRAFormValidationWarning(BaseModel):
    field: str
    message: str
    suggestion: Optional[str]


class KRAFormValidationResponse(BaseModel):
    is_valid: bool
    errors: List[KRAFormValidationError]
    warnings: List[KRAFormValidationWarning]
    validation_id: str