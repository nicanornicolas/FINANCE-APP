"""
KRA Tax API Router
Endpoints for KRA tax preparation, calculation, and filing
"""
from typing import List, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, get_current_user
from app.models.user import User
from app.services.kra_tax_service import kra_tax_service
from app.schemas.kra_tax import (
    KRATaxpayerCreate, KRATaxpayerResponse, KRATaxpayerUpdate,
    KRATaxFilingCreate, KRATaxFilingResponse, KRATaxFilingUpdate,
    KRATaxCalculationResponse,
    KRAPINValidationRequest, KRAPINValidationResponse,
    KRATaxDeductionCreate, KRATaxDeductionResponse,
    KRATaxPaymentCreate, KRATaxPaymentResponse
)

router = APIRouter()


@router.post("/validate-pin", response_model=KRAPINValidationResponse)
async def validate_kra_pin(
    *,
    pin_data: KRAPINValidationRequest,
    current_user: User = Depends(get_current_user)
):
    """Validate KRA PIN with KRA iTax system"""
    try:
        return await kra_tax_service.validate_kra_pin(pin_data.kra_pin)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/taxpayer", response_model=KRATaxpayerResponse)
def register_taxpayer(
    *,
    db: Session = Depends(get_db),
    taxpayer_data: KRATaxpayerCreate,
    current_user: User = Depends(get_current_user)
):
    """Register new taxpayer"""
    try:
        return kra_tax_service.register_taxpayer(
            db, taxpayer_data=taxpayer_data, user_id=current_user.id
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register taxpayer"
        )


@router.get("/taxpayer", response_model=KRATaxpayerResponse)
def get_taxpayer(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user's taxpayer information"""
    taxpayer = kra_tax_service.get_user_taxpayer(db, user_id=current_user.id)
    if not taxpayer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Taxpayer not found"
        )
    return taxpayer


@router.post("/taxpayer/{taxpayer_id}/verify", response_model=KRATaxpayerResponse)
async def verify_taxpayer(
    *,
    db: Session = Depends(get_db),
    taxpayer_id: UUID,
    current_user: User = Depends(get_current_user)
):
    """Verify taxpayer with KRA"""
    try:
        return await kra_tax_service.verify_taxpayer(db, taxpayer_id=taxpayer_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify taxpayer"
        )


@router.post("/filings", response_model=KRATaxFilingResponse)
def create_tax_filing(
    *,
    db: Session = Depends(get_db),
    filing_data: KRATaxFilingCreate,
    current_user: User = Depends(get_current_user)
):
    """Create new tax filing"""
    try:
        return kra_tax_service.create_tax_filing(
            db, filing_data=filing_data, user_id=current_user.id
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create tax filing"
        )


@router.get("/filings", response_model=List[KRATaxFilingResponse])
def get_tax_filings(
    *,
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user)
):
    """Get user's tax filings"""
    return kra_tax_service.get_user_filings(
        db, user_id=current_user.id, skip=skip, limit=limit
    )


@router.post("/filings/{filing_id}/calculate", response_model=KRATaxCalculationResponse)
async def calculate_tax(
    *,
    db: Session = Depends(get_db),
    filing_id: UUID,
    current_user: User = Depends(get_current_user)
):
    """Calculate tax for filing"""
    try:
        return await kra_tax_service.calculate_tax(
            db, user_id=current_user.id, filing_id=filing_id
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to calculate tax"
        )


@router.post("/filings/{filing_id}/submit")
async def submit_tax_filing(
    *,
    db: Session = Depends(get_db),
    filing_id: UUID,
    current_user: User = Depends(get_current_user)
):
    """Submit tax filing to KRA"""
    try:
        return await kra_tax_service.submit_tax_filing(
            db, user_id=current_user.id, filing_id=filing_id
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit tax filing"
        )


@router.get("/filings/{filing_id}/status")
async def get_filing_status(
    *,
    db: Session = Depends(get_db),
    filing_id: UUID,
    current_user: User = Depends(get_current_user)
):
    """Get filing status from KRA"""
    try:
        return await kra_tax_service.get_filing_status(
            db, user_id=current_user.id, filing_id=filing_id
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get filing status"
        )


@router.post("/deductions", response_model=KRATaxDeductionResponse)
def add_tax_deduction(
    *,
    db: Session = Depends(get_db),
    deduction_data: KRATaxDeductionCreate,
    current_user: User = Depends(get_current_user)
):
    """Add tax deduction"""
    try:
        deduction = kra_tax_service.add_tax_deduction(
            db, deduction_data=deduction_data, user_id=current_user.id
        )
        return KRATaxDeductionResponse.from_orm(deduction)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add tax deduction"
        )


@router.get("/deductions/{tax_year}", response_model=List[KRATaxDeductionResponse])
def get_tax_deductions(
    *,
    db: Session = Depends(get_db),
    tax_year: int,
    current_user: User = Depends(get_current_user)
):
    """Get tax deductions for year"""
    deductions = kra_tax_service.get_user_deductions(
        db, user_id=current_user.id, tax_year=tax_year
    )
    return [KRATaxDeductionResponse.from_orm(deduction) for deduction in deductions]


@router.get("/forms/{tax_year}")
async def get_tax_forms(
    *,
    db: Session = Depends(get_db),
    tax_year: int,
    current_user: User = Depends(get_current_user)
):
    """Get available tax forms for year"""
    # This would return available KRA tax forms
    return {
        "tax_year": tax_year,
        "available_forms": [
            {
                "form_type": "individual",
                "form_name": "Individual Income Tax Return (IT1)",
                "description": "For individual taxpayers filing income tax returns"
            },
            {
                "form_type": "vat",
                "form_name": "VAT Return (VAT 3)",
                "description": "For VAT registered businesses"
            },
            {
                "form_type": "withholding",
                "form_name": "Withholding Tax Return",
                "description": "For withholding tax obligations"
            },
            {
                "form_type": "turnover",
                "form_name": "Turnover Tax Return",
                "description": "For small businesses under turnover tax"
            }
        ]
    }


@router.get("/tax-rates/{tax_year}")
async def get_tax_rates(
    *,
    tax_year: int,
    current_user: User = Depends(get_current_user)
):
    """Get tax rates for year"""
    try:
        return await kra_tax_service.calculator.get_tax_rates(tax_year)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get tax rates"
        )


@router.get("/dashboard")
def get_tax_dashboard(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get tax dashboard data"""
    from datetime import datetime
    current_year = datetime.now().year
    
    # Get recent filings
    recent_filings = kra_tax_service.get_user_filings(db, user_id=current_user.id, limit=5)
    
    # Get taxpayer info
    taxpayer = kra_tax_service.get_user_taxpayer(db, user_id=current_user.id)
    
    return {
        "taxpayer": taxpayer,
        "recent_filings": recent_filings,
        "current_tax_year": current_year,
        "filing_deadlines": {
            "individual_income_tax": f"{current_year + 1}-06-30",
            "vat_return": f"{current_year}-{datetime.now().month + 1:02d}-20",
            "withholding_tax": f"{current_year}-{datetime.now().month + 1:02d}-20"
        },
        "quick_actions": [
            {"action": "file_individual_tax", "label": "File Individual Tax Return"},
            {"action": "add_deduction", "label": "Add Tax Deduction"},
            {"action": "check_filing_status", "label": "Check Filing Status"},
            {"action": "make_payment", "label": "Make Tax Payment"}
        ]
    }