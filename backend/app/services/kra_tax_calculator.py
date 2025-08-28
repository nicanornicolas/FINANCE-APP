"""
KRA Tax Calculation Service
Implements Kenyan tax calculation logic according to KRA guidelines
"""
import logging
from typing import Dict, List, Any, Optional
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, date

from app.schemas.kra_tax import (
    KRATaxCalculationRequest,
    KRATaxCalculationResponse,
    KRAFilingType,
    KRAIndividualTaxForm,
    KRAVATForm
)
from app.services.kra_api_client import KRAAPIClient, MockKRAAPIClient
from app.core.config import settings

logger = logging.getLogger(__name__)


class KRATaxCalculator:
    """Service for calculating Kenyan taxes according to KRA rules"""
    
    def __init__(self):
        # Use mock client for development, real client for production
        self.kra_client = MockKRAAPIClient() if getattr(settings, 'USE_MOCK_KRA', True) else KRAAPIClient()
        
        # Cache for tax rates to avoid frequent API calls
        self._tax_rates_cache = {}
    
    async def get_tax_rates(self, tax_year: int) -> Dict[str, Any]:
        """Get tax rates for given year, with caching"""
        if tax_year in self._tax_rates_cache:
            return self._tax_rates_cache[tax_year]
        
        try:
            async with self.kra_client as client:
                rates = await client.get_tax_rates(tax_year)
                self._tax_rates_cache[tax_year] = rates
                return rates
        except Exception as e:
            logger.error(f"Failed to get tax rates for {tax_year}: {str(e)}")
            # Fallback to default rates
            return self._get_default_tax_rates(tax_year)
    
    def _get_default_tax_rates(self, tax_year: int) -> Dict[str, Any]:
        """Default tax rates as fallback"""
        return {
            "tax_year": tax_year,
            "individual_rates": [
                {"min_income": 0, "max_income": 288000, "rate": 0.10},
                {"min_income": 288001, "max_income": 388000, "rate": 0.25},
                {"min_income": 388001, "max_income": 6000000, "rate": 0.30},
                {"min_income": 6000001, "max_income": 9600000, "rate": 0.325},
                {"min_income": 9600001, "max_income": None, "rate": 0.35}
            ],
            "reliefs": {
                "personal_relief": 28800,
                "insurance_relief_limit": 60000,
                "mortgage_interest_limit": 300000
            },
            "vat_rate": 0.16,
            "withholding_rates": {
                "dividends": 0.05,
                "interest": 0.15,
                "rent": 0.10,
                "professional_fees": 0.05
            }
        }
    
    async def calculate_individual_tax(self, request: KRATaxCalculationRequest) -> KRATaxCalculationResponse:
        """Calculate individual income tax"""
        tax_rates = await self.get_tax_rates(request.tax_year)
        
        # Extract income components
        employment_income = request.income_data.get("employment", Decimal("0"))
        business_income = request.income_data.get("business", Decimal("0"))
        rental_income = request.income_data.get("rental", Decimal("0"))
        investment_income = request.income_data.get("investment", Decimal("0"))
        other_income = request.income_data.get("other", Decimal("0"))
        
        gross_income = employment_income + business_income + rental_income + investment_income + other_income
        
        # Calculate deductions
        total_deductions = self._calculate_deductions(request.deductions, tax_rates["reliefs"])
        
        # Calculate taxable income
        taxable_income = max(gross_income - total_deductions, Decimal("0"))
        
        # Calculate tax using brackets
        calculated_tax, tax_brackets = self._calculate_tax_brackets(taxable_income, tax_rates["individual_rates"])
        
        # Apply personal relief
        personal_relief = Decimal(str(tax_rates["reliefs"]["personal_relief"]))
        final_tax = max(calculated_tax - personal_relief, Decimal("0"))
        
        # Calculate rates
        effective_rate = float(final_tax / gross_income * 100) if gross_income > 0 else 0.0
        marginal_rate = self._get_marginal_rate(taxable_income, tax_rates["individual_rates"])
        
        return KRATaxCalculationResponse(
            tax_year=request.tax_year,
            filing_type=request.filing_type,
            gross_income=gross_income,
            taxable_income=taxable_income,
            total_deductions=total_deductions,
            calculated_tax=final_tax,
            tax_brackets=tax_brackets,
            effective_rate=round(effective_rate, 2),
            marginal_rate=marginal_rate
        )
    
    def _calculate_deductions(self, deductions: List[Dict[str, Any]], reliefs: Dict[str, Any]) -> Decimal:
        """Calculate total allowable deductions"""
        total = Decimal("0")
        
        for deduction in deductions:
            deduction_type = deduction.get("type", "").lower()
            amount = Decimal(str(deduction.get("amount", 0)))
            
            if deduction_type == "insurance":
                # Insurance relief is limited
                limit = Decimal(str(reliefs.get("insurance_relief_limit", 60000)))
                total += min(amount, limit)
            elif deduction_type == "mortgage_interest":
                # Mortgage interest relief is limited
                limit = Decimal(str(reliefs.get("mortgage_interest_limit", 300000)))
                total += min(amount, limit)
            elif deduction_type == "pension":
                # Pension contributions (usually unlimited for approved schemes)
                total += amount
            elif deduction_type == "nhif":
                # NHIF contributions are fully deductible
                total += amount
            elif deduction_type == "nssf":
                # NSSF contributions are fully deductible
                total += amount
            else:
                # Other allowable deductions
                total += amount
        
        return total
    
    def _calculate_tax_brackets(self, taxable_income: Decimal, brackets: List[Dict[str, Any]]) -> tuple[Decimal, List[Dict[str, Any]]]:
        """Calculate tax using progressive brackets"""
        total_tax = Decimal("0")
        tax_breakdown = []
        remaining_income = taxable_income
        
        for bracket in brackets:
            min_income = Decimal(str(bracket["min_income"]))
            max_income = Decimal(str(bracket["max_income"])) if bracket["max_income"] else None
            rate = Decimal(str(bracket["rate"]))
            
            if remaining_income <= 0:
                break
            
            # Calculate taxable amount in this bracket
            if max_income is None:
                # Top bracket - all remaining income
                bracket_income = remaining_income
            else:
                bracket_income = min(remaining_income, max_income - min_income + 1)
            
            if bracket_income > 0:
                bracket_tax = bracket_income * rate
                total_tax += bracket_tax
                
                tax_breakdown.append({
                    "bracket": f"{min_income:,.0f} - {max_income:,.0f}" if max_income else f"{min_income:,.0f}+",
                    "rate": float(rate * 100),
                    "taxable_amount": float(bracket_income),
                    "tax_amount": float(bracket_tax)
                })
                
                remaining_income -= bracket_income
        
        return total_tax.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), tax_breakdown
    
    def _get_marginal_rate(self, taxable_income: Decimal, brackets: List[Dict[str, Any]]) -> float:
        """Get marginal tax rate for given income"""
        for bracket in brackets:
            min_income = Decimal(str(bracket["min_income"]))
            max_income = Decimal(str(bracket["max_income"])) if bracket["max_income"] else None
            
            if max_income is None or taxable_income <= max_income:
                return float(bracket["rate"] * 100)
        
        return float(brackets[-1]["rate"] * 100)
    
    async def calculate_vat(self, request: KRATaxCalculationRequest) -> KRATaxCalculationResponse:
        """Calculate VAT for business"""
        tax_rates = await self.get_tax_rates(request.tax_year)
        vat_rate = Decimal(str(tax_rates.get("vat_rate", 0.16)))
        
        # Extract VAT-related income data
        standard_rated_sales = request.income_data.get("standard_rated_sales", Decimal("0"))
        zero_rated_sales = request.income_data.get("zero_rated_sales", Decimal("0"))
        exempt_sales = request.income_data.get("exempt_sales", Decimal("0"))
        
        standard_rated_purchases = request.income_data.get("standard_rated_purchases", Decimal("0"))
        zero_rated_purchases = request.income_data.get("zero_rated_purchases", Decimal("0"))
        
        # Calculate output VAT
        output_vat = standard_rated_sales * vat_rate
        
        # Calculate input VAT
        input_vat = standard_rated_purchases * vat_rate
        
        # Net VAT
        net_vat = output_vat - input_vat
        vat_payable = max(net_vat, Decimal("0"))
        
        total_sales = standard_rated_sales + zero_rated_sales + exempt_sales
        
        return KRATaxCalculationResponse(
            tax_year=request.tax_year,
            filing_type=request.filing_type,
            gross_income=total_sales,
            taxable_income=standard_rated_sales,
            total_deductions=input_vat,
            calculated_tax=vat_payable,
            tax_brackets=[{
                "bracket": "VAT",
                "rate": float(vat_rate * 100),
                "taxable_amount": float(standard_rated_sales),
                "tax_amount": float(output_vat)
            }],
            effective_rate=float(vat_payable / total_sales * 100) if total_sales > 0 else 0.0,
            marginal_rate=float(vat_rate * 100)
        )
    
    async def calculate_withholding_tax(self, request: KRATaxCalculationRequest) -> KRATaxCalculationResponse:
        """Calculate withholding tax"""
        tax_rates = await self.get_tax_rates(request.tax_year)
        wht_rates = tax_rates.get("withholding_rates", {})
        
        total_wht = Decimal("0")
        tax_breakdown = []
        gross_income = Decimal("0")
        
        for income_type, amount in request.income_data.items():
            amount = Decimal(str(amount))
            gross_income += amount
            
            if income_type in wht_rates:
                rate = Decimal(str(wht_rates[income_type]))
                wht_amount = amount * rate
                total_wht += wht_amount
                
                tax_breakdown.append({
                    "bracket": income_type.replace("_", " ").title(),
                    "rate": float(rate * 100),
                    "taxable_amount": float(amount),
                    "tax_amount": float(wht_amount)
                })
        
        return KRATaxCalculationResponse(
            tax_year=request.tax_year,
            filing_type=request.filing_type,
            gross_income=gross_income,
            taxable_income=gross_income,
            total_deductions=Decimal("0"),
            calculated_tax=total_wht,
            tax_brackets=tax_breakdown,
            effective_rate=float(total_wht / gross_income * 100) if gross_income > 0 else 0.0,
            marginal_rate=0.0  # WHT is flat rate
        )
    
    async def calculate_tax(self, request: KRATaxCalculationRequest) -> KRATaxCalculationResponse:
        """Main tax calculation method - routes to appropriate calculator"""
        try:
            if request.filing_type == KRAFilingType.INDIVIDUAL:
                return await self.calculate_individual_tax(request)
            elif request.filing_type == KRAFilingType.VAT:
                return await self.calculate_vat(request)
            elif request.filing_type == KRAFilingType.WITHHOLDING:
                return await self.calculate_withholding_tax(request)
            else:
                raise ValueError(f"Unsupported filing type: {request.filing_type}")
        
        except Exception as e:
            logger.error(f"Tax calculation error: {str(e)}")
            raise
    
    def generate_individual_tax_form(self, calculation: KRATaxCalculationResponse, taxpayer_info: Dict[str, Any]) -> KRAIndividualTaxForm:
        """Generate Individual Tax Form (IT1) from calculation"""
        return KRAIndividualTaxForm(
            taxpayer_info=taxpayer_info,
            employment_income=calculation.gross_income,  # Simplified - would need breakdown
            business_income=Decimal("0"),
            rental_income=Decimal("0"),
            investment_income=Decimal("0"),
            other_income=Decimal("0"),
            total_income=calculation.gross_income,
            
            insurance_relief=Decimal("0"),  # Would extract from deductions
            mortgage_interest=Decimal("0"),
            pension_contributions=Decimal("0"),
            other_deductions=Decimal("0"),
            total_deductions=calculation.total_deductions,
            
            taxable_income=calculation.taxable_income,
            tax_payable=calculation.calculated_tax,
            withholding_tax=Decimal("0"),
            advance_tax=Decimal("0"),
            balance_due=calculation.calculated_tax
        )
    
    def generate_vat_form(self, calculation: KRATaxCalculationResponse, taxpayer_info: Dict[str, Any], tax_period: str) -> KRAVATForm:
        """Generate VAT Form (VAT 3) from calculation"""
        return KRAVATForm(
            taxpayer_info=taxpayer_info,
            tax_period=tax_period,
            
            standard_rated_sales=calculation.taxable_income,
            zero_rated_sales=Decimal("0"),
            exempt_sales=Decimal("0"),
            total_sales=calculation.gross_income,
            output_vat=calculation.calculated_tax + calculation.total_deductions,  # Simplified
            
            standard_rated_purchases=Decimal("0"),
            zero_rated_purchases=Decimal("0"),
            exempt_purchases=Decimal("0"),
            total_purchases=Decimal("0"),
            input_vat=calculation.total_deductions,
            
            net_vat=calculation.calculated_tax,
            vat_payable=calculation.calculated_tax
        )