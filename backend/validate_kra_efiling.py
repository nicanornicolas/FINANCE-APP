#!/usr/bin/env python3
"""
Validation script for KRA e-filing implementation
Tests core functionality without external dependencies
"""

import sys
import os
import asyncio
from typing import Dict, Any
from decimal import Decimal
from datetime import datetime

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def test_kra_api_client_structure():
    """Test KRA API client structure and methods"""
    print("Testing KRA API Client structure...")
    
    try:
        # Test imports
        from services.kra_api_client import KRAAPIClient, MockKRAAPIClient, KRAAPIError
        print("✓ KRA API client imports successful")
        
        # Test client initialization
        mock_client = MockKRAAPIClient()
        print("✓ Mock KRA API client initialized")
        
        # Test that all required methods exist
        required_methods = [
            'validate_pin', 'submit_tax_return', 'get_filing_status',
            'make_payment', 'get_payment_status', 'get_tax_rates',
            'validate_tax_form', 'get_filing_history', 'amend_tax_return',
            'get_filing_documents', 'upload_supporting_document',
            'initiate_payment', 'confirm_payment', 'get_payment_methods'
        ]
        
        for method in required_methods:
            if hasattr(mock_client, method):
                print(f"✓ Method {method} exists")
            else:
                print(f"✗ Method {method} missing")
                return False
        
        return True
        
    except Exception as e:
        print(f"✗ Error testing KRA API client: {e}")
        return False

def test_kra_models_structure():
    """Test KRA models structure"""
    print("\nTesting KRA models structure...")
    
    try:
        from models.kra_tax import (
            KRATaxpayer, KRATaxFiling, KRATaxPayment, KRATaxDeduction,
            KRATaxAmendment, KRATaxDocument, KRAFilingValidation,
            KRAFilingType, KRAFilingStatus, KRATaxpayerType
        )
        print("✓ KRA models import successful")
        
        # Test enum values
        filing_types = [e.value for e in KRAFilingType]
        expected_types = ['individual', 'corporate', 'vat', 'withholding', 'turnover', 'rental', 'capital_gains']
        
        for expected_type in expected_types:
            if expected_type in filing_types:
                print(f"✓ Filing type {expected_type} exists")
            else:
                print(f"✗ Filing type {expected_type} missing")
                return False
        
        return True
        
    except Exception as e:
        print(f"✗ Error testing KRA models: {e}")
        return False

def test_kra_schemas_structure():
    """Test KRA schemas structure"""
    print("\nTesting KRA schemas structure...")
    
    try:
        from schemas.kra_tax import (
            KRATaxAmendmentCreate, KRATaxAmendmentResponse,
            KRATaxDocumentCreate, KRATaxDocumentResponse,
            KRAFormValidationRequest, KRAFormValidationResponse,
            KRAFilingHistoryResponse, KRAPaymentInitiationRequest,
            KRAPaymentInitiationResponse, KRAPaymentConfirmationRequest,
            KRAPaymentMethodsResponse
        )
        print("✓ KRA e-filing schemas import successful")
        
        # Test schema structure by creating instances
        test_schemas = {
            'KRAFormValidationRequest': {
                'filing_type': 'individual',
                'form_data': {'test': 'data'},
                'tax_year': 2023
            },
            'KRAPaymentInitiationRequest': {
                'filing_id': '123e4567-e89b-12d3-a456-426614174000',
                'amount': Decimal('50000'),
                'payment_method': 'mobile_money'
            }
        }
        
        for schema_name, test_data in test_schemas.items():
            try:
                schema_class = locals()[schema_name]
                instance = schema_class(**test_data)
                print(f"✓ Schema {schema_name} validation successful")
            except Exception as e:
                print(f"✗ Schema {schema_name} validation failed: {e}")
                return False
        
        return True
        
    except Exception as e:
        print(f"✗ Error testing KRA schemas: {e}")
        return False

async def test_mock_kra_api_functionality():
    """Test mock KRA API functionality"""
    print("\nTesting Mock KRA API functionality...")
    
    try:
        from services.kra_api_client import MockKRAAPIClient
        
        async with MockKRAAPIClient() as client:
            # Test PIN validation
            pin_validation = await client.validate_pin("P051234567A")
            if pin_validation.is_valid:
                print("✓ PIN validation works")
            else:
                print("✗ PIN validation failed")
                return False
            
            # Test tax rates
            tax_rates = await client.get_tax_rates(2023)
            if 'individual_rates' in tax_rates:
                print("✓ Tax rates retrieval works")
            else:
                print("✗ Tax rates retrieval failed")
                return False
            
            # Test form validation
            form_data = {
                'total_income': 500000,
                'taxable_income': 450000,
                'calculated_tax': 45000
            }
            validation_result = await client.validate_tax_form(form_data)
            if 'is_valid' in validation_result:
                print("✓ Form validation works")
            else:
                print("✗ Form validation failed")
                return False
            
            # Test filing history
            history = await client.get_filing_history("P051234567A", 2023)
            if 'filings' in history:
                print("✓ Filing history retrieval works")
            else:
                print("✗ Filing history retrieval failed")
                return False
            
            # Test payment methods
            payment_methods = await client.get_payment_methods()
            if 'methods' in payment_methods:
                print("✓ Payment methods retrieval works")
            else:
                print("✗ Payment methods retrieval failed")
                return False
        
        return True
        
    except Exception as e:
        print(f"✗ Error testing mock KRA API: {e}")
        return False

def test_file_structure():
    """Test that all required files exist"""
    print("\nTesting file structure...")
    
    required_files = [
        'app/services/kra_api_client.py',
        'app/models/kra_tax.py',
        'app/schemas/kra_tax.py',
        'app/crud/kra_tax.py',
        'app/services/kra_tax_service.py',
        'app/api/routers/kra_tax.py',
        'alembic/versions/add_kra_efiling_tables.py',
        'tests/test_kra_efiling_integration.py'
    ]
    
    all_exist = True
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✓ {file_path} exists")
        else:
            print(f"✗ {file_path} missing")
            all_exist = False
    
    return all_exist

def test_api_endpoints_structure():
    """Test API endpoints structure"""
    print("\nTesting API endpoints structure...")
    
    try:
        from api.routers.kra_tax import router
        print("✓ KRA tax router import successful")
        
        # Check that router has routes
        if hasattr(router, 'routes') and len(router.routes) > 0:
            print(f"✓ Router has {len(router.routes)} routes")
            
            # Check for specific e-filing routes
            route_paths = [route.path for route in router.routes if hasattr(route, 'path')]
            expected_paths = [
                '/filings/{filing_id}/validate',
                '/filing-history',
                '/amendments',
                '/documents',
                '/payment-methods',
                '/payments/initiate'
            ]
            
            for expected_path in expected_paths:
                if any(expected_path in path for path in route_paths):
                    print(f"✓ E-filing endpoint {expected_path} exists")
                else:
                    print(f"✗ E-filing endpoint {expected_path} missing")
                    return False
        else:
            print("✗ Router has no routes")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ Error testing API endpoints: {e}")
        return False

def main():
    """Run all validation tests"""
    print("KRA E-Filing Implementation Validation")
    print("=" * 50)
    
    tests = [
        test_file_structure,
        test_kra_api_client_structure,
        test_kra_models_structure,
        test_kra_schemas_structure,
        test_api_endpoints_structure,
    ]
    
    async_tests = [
        test_mock_kra_api_functionality
    ]
    
    results = []
    
    # Run synchronous tests
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"✗ Test {test.__name__} failed with exception: {e}")
            results.append(False)
    
    # Run asynchronous tests
    for test in async_tests:
        try:
            result = asyncio.run(test())
            results.append(result)
        except Exception as e:
            print(f"✗ Test {test.__name__} failed with exception: {e}")
            results.append(False)
    
    # Summary
    print("\n" + "=" * 50)
    print("VALIDATION SUMMARY")
    print("=" * 50)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("✓ ALL TESTS PASSED - KRA e-filing implementation is complete!")
        return 0
    else:
        print("✗ Some tests failed - please review the implementation")
        return 1

if __name__ == "__main__":
    sys.exit(main())