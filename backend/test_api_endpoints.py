#!/usr/bin/env python3
"""
Test API endpoints for ML categorization
"""

import sys
import os
from pathlib import Path

# Add the app directory to Python path
sys.path.append(str(Path(__file__).parent))

from fastapi.testclient import TestClient
from app.main import app
from unittest.mock import patch, Mock
from uuid import uuid4


def test_api_endpoints():
    """Test ML categorization API endpoints"""
    print("Testing ML Categorization API Endpoints")
    print("=" * 50)
    
    client = TestClient(app)
    
    # Mock user for authentication
    mock_user = Mock()
    mock_user.id = uuid4()
    mock_user.email = "test@example.com"
    
    print("\n1. Testing model info endpoint (no auth required for this test):")
    
    # Test without authentication first to see the structure
    with patch('app.api.routers.categorization.get_current_user', return_value=mock_user):
        response = client.get('/api/categorization/model/info')
        print(f"  Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  Response: {data}")
        else:
            print(f"  Error: {response.json()}")
    
    print("\n2. Testing prediction endpoint:")
    
    with patch('app.api.routers.categorization.get_current_user', return_value=mock_user), \
         patch('app.api.routers.categorization.ml_categorization_service') as mock_service:
        
        # Mock the ML service response
        mock_service.predict_category.return_value = {
            'predicted_category': 'Groceries',
            'confidence': 0.85,
            'all_predictions': [
                {'category': 'Groceries', 'confidence': 0.85},
                {'category': 'Shopping', 'confidence': 0.10},
                {'category': 'Food', 'confidence': 0.05}
            ],
            'needs_manual_review': False
        }
        
        request_data = {
            'description': 'WALMART SUPERCENTER',
            'amount': -45.67,
            'transaction_type': 'expense'
        }
        
        response = client.post('/api/categorization/predict', json=request_data)
        print(f"  Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  Predicted category: {data['predicted_category']}")
            print(f"  Confidence: {data['confidence']}")
            print(f"  Needs review: {data['needs_manual_review']}")
            print(f"  All predictions: {len(data['all_predictions'])} options")
        else:
            print(f"  Error: {response.json()}")
    
    print("\n3. Testing bulk prediction endpoint:")
    
    with patch('app.api.routers.categorization.get_current_user', return_value=mock_user), \
         patch('app.api.routers.categorization.ml_categorization_service') as mock_service:
        
        # Mock the ML service response
        mock_service.predict_category.return_value = {
            'predicted_category': 'Groceries',
            'confidence': 0.75,
            'all_predictions': [{'category': 'Groceries', 'confidence': 0.75}],
            'needs_manual_review': False
        }
        
        request_data = {
            'transactions': [
                {
                    'description': 'WALMART SUPERCENTER',
                    'amount': -45.67,
                    'transaction_type': 'expense'
                },
                {
                    'description': 'SHELL GAS STATION',
                    'amount': -32.50,
                    'transaction_type': 'expense'
                }
            ]
        }
        
        response = client.post('/api/categorization/predict/bulk', json=request_data)
        print(f"  Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  Total processed: {data['total_processed']}")
            print(f"  High confidence: {data['high_confidence_count']}")
            print(f"  Needs review: {data['needs_review_count']}")
        else:
            print(f"  Error: {response.json()}")
    
    print("\n4. Testing validation errors:")
    
    with patch('app.api.routers.categorization.get_current_user', return_value=mock_user):
        # Test with invalid data
        invalid_request = {
            'description': '',  # Empty description
            'amount': 'invalid'  # Invalid amount
        }
        
        response = client.post('/api/categorization/predict', json=invalid_request)
        print(f"  Status for invalid data: {response.status_code}")
        if response.status_code == 422:
            print("  ✓ Validation error correctly returned")
        else:
            print(f"  Unexpected response: {response.json()}")
    
    print("\nAPI Endpoints test completed!")
    print("\nEndpoints implemented:")
    print("- POST /api/categorization/predict - Single prediction")
    print("- POST /api/categorization/predict/bulk - Bulk predictions")
    print("- POST /api/categorization/correct - Manual correction")
    print("- POST /api/categorization/train - Train model")
    print("- POST /api/categorization/retrain - Retrain model")
    print("- GET /api/categorization/model/info - Model information")
    print("- GET /api/categorization/stats - Categorization statistics")
    print("- POST /api/categorization/auto-categorize/{id} - Auto-categorize transaction")


if __name__ == "__main__":
    test_api_endpoints()