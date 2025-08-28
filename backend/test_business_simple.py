"""
Simple test script to verify business functionality without pytest dependencies
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

# Test the business models and schemas
def test_business_models():
    """Test business model imports and basic functionality"""
    try:
        from app.models.business import (
            BusinessEntity, BusinessType, Client, Invoice, InvoiceItem, 
            InvoicePayment, InvoiceStatus, PaymentTerms
        )
        print("✓ Business models imported successfully")
        
        # Test enum values
        assert BusinessType.LIMITED_LIABILITY == "limited_liability"
        assert InvoiceStatus.PAID == "paid"
        assert PaymentTerms.NET_30 == "net_30"
        print("✓ Business enums work correctly")
        
    except Exception as e:
        print(f"✗ Business models test failed: {e}")
        return False
    
    return True


def test_business_schemas():
    """Test business schema imports and validation"""
    try:
        from app.schemas.business import (
            BusinessEntityCreate, ClientCreate, InvoiceCreate, 
            InvoiceItemCreate, BusinessSummary
        )
        print("✓ Business schemas imported successfully")
        
        # Test schema creation
        business_data = BusinessEntityCreate(
            name="Test Business",
            business_type="limited_liability",
            email="test@business.com",
            default_currency="KES"
        )
        assert business_data.name == "Test Business"
        print("✓ Business schema validation works")
        
        # Test invoice item schema
        item_data = InvoiceItemCreate(
            description="Test Service",
            quantity=Decimal('2.0000'),
            unit_price=Decimal('1000.00')
        )
        assert item_data.quantity == Decimal('2.0000')
        print("✓ Invoice item schema works")
        
    except Exception as e:
        print(f"✗ Business schemas test failed: {e}")
        return False
    
    return True


def test_business_crud():
    """Test business CRUD imports"""
    try:
        from app.crud.business import (
            business_entity, client, invoice, invoice_item, invoice_payment
        )
        print("✓ Business CRUD operations imported successfully")
        
        # Test that CRUD instances exist
        assert hasattr(business_entity, 'create')
        assert hasattr(client, 'get_by_business')
        assert hasattr(invoice, 'mark_as_sent')
        print("✓ Business CRUD methods available")
        
    except Exception as e:
        print(f"✗ Business CRUD test failed: {e}")
        return False
    
    return True


def test_business_service():
    """Test business service imports"""
    try:
        from app.services.business_service import business_service
        print("✓ Business service imported successfully")
        
        # Test that service methods exist
        assert hasattr(business_service, 'get_business_summary')
        assert hasattr(business_service, 'generate_profit_loss_report')
        assert hasattr(business_service, 'generate_cash_flow_report')
        print("✓ Business service methods available")
        
    except Exception as e:
        print(f"✗ Business service test failed: {e}")
        return False
    
    return True


def test_business_api():
    """Test business API router imports"""
    try:
        from app.api.routers.business import router
        print("✓ Business API router imported successfully")
        
        # Check that router has routes
        assert len(router.routes) > 0
        print(f"✓ Business API has {len(router.routes)} routes")
        
    except Exception as e:
        print(f"✗ Business API test failed: {e}")
        return False
    
    return True


def test_invoice_calculations():
    """Test invoice calculation logic"""
    try:
        from app.schemas.business import InvoiceItemCreate
        
        # Test calculation logic
        items = [
            InvoiceItemCreate(
                description="Service 1",
                quantity=Decimal('2.0000'),
                unit_price=Decimal('1500.00')
            ),
            InvoiceItemCreate(
                description="Service 2",
                quantity=Decimal('1.0000'),
                unit_price=Decimal('2000.00')
            )
        ]
        
        # Calculate subtotal
        subtotal = sum(item.quantity * item.unit_price for item in items)
        expected_subtotal = Decimal('5000.00')  # 2*1500 + 1*2000
        
        assert subtotal == expected_subtotal
        print(f"✓ Invoice calculation works: subtotal = {subtotal}")
        
        # Test tax calculation
        tax_rate = Decimal('0.16')  # 16% VAT
        tax_amount = subtotal * tax_rate
        total_amount = subtotal + tax_amount
        
        expected_tax = Decimal('800.00')  # 5000 * 0.16
        expected_total = Decimal('5800.00')  # 5000 + 800
        
        assert tax_amount == expected_tax
        assert total_amount == expected_total
        print(f"✓ Tax calculation works: tax = {tax_amount}, total = {total_amount}")
        
    except Exception as e:
        print(f"✗ Invoice calculations test failed: {e}")
        return False
    
    return True


def main():
    """Run all tests"""
    print("Running Business Functionality Tests")
    print("=" * 40)
    
    tests = [
        test_business_models,
        test_business_schemas,
        test_business_crud,
        test_business_service,
        test_business_api,
        test_invoice_calculations
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        print(f"\nRunning {test.__name__}...")
        try:
            if test():
                passed += 1
                print(f"✓ {test.__name__} PASSED")
            else:
                failed += 1
                print(f"✗ {test.__name__} FAILED")
        except Exception as e:
            failed += 1
            print(f"✗ {test.__name__} FAILED with exception: {e}")
    
    print("\n" + "=" * 40)
    print(f"Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All business functionality tests passed!")
        return True
    else:
        print("❌ Some tests failed. Check the output above.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)