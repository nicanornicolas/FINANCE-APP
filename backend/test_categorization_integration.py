#!/usr/bin/env python3
"""
Integration test for ML categorization functionality
"""

import sys
import os
from pathlib import Path

# Add the app directory to Python path
sys.path.append(str(Path(__file__).parent))

from app.services.ml_categorization import MLCategorizationService
from app.schemas.categorization import PredictionRequest, PredictionResponse
from datetime import datetime


def test_categorization_integration():
    """Test ML categorization integration"""
    print("Testing ML Categorization Integration")
    print("=" * 50)
    
    # Initialize service
    service = MLCategorizationService()
    
    # Test prediction request/response schemas
    print("\n1. Testing Pydantic schemas:")
    
    # Test PredictionRequest
    request = PredictionRequest(
        description="WALMART SUPERCENTER",
        amount=-45.67,
        transaction_type="expense",
        date=datetime(2024, 1, 15)
    )
    print(f"  PredictionRequest: {request}")
    
    # Test prediction (without model)
    prediction_result = service.predict_category(
        description=request.description,
        amount=request.amount,
        transaction_type=request.transaction_type,
        date=request.date
    )
    
    # Test PredictionResponse
    response = PredictionResponse(**prediction_result)
    print(f"  PredictionResponse: {response}")
    print()
    
    # Test bulk prediction data
    print("2. Testing bulk prediction structure:")
    transactions = [
        {
            'description': 'WALMART SUPERCENTER',
            'amount': -45.67,
            'transaction_type': 'expense',
            'date': datetime(2024, 1, 15)
        },
        {
            'description': 'SHELL GAS STATION',
            'amount': -32.50,
            'transaction_type': 'expense',
            'date': datetime(2024, 1, 16)
        },
        {
            'description': 'MCDONALD\'S RESTAURANT',
            'amount': -12.99,
            'transaction_type': 'expense',
            'date': datetime(2024, 1, 17)
        }
    ]
    
    predictions = []
    high_confidence_count = 0
    needs_review_count = 0
    
    for trans in transactions:
        prediction = service.predict_category(
            description=trans['description'],
            amount=trans['amount'],
            transaction_type=trans['transaction_type'],
            date=trans['date']
        )
        
        prediction_response = PredictionResponse(**prediction)
        predictions.append(prediction_response)
        
        if prediction_response.needs_manual_review:
            needs_review_count += 1
        else:
            high_confidence_count += 1
        
        print(f"  Transaction: {trans['description']}")
        print(f"    Prediction: {prediction_response.predicted_category}")
        print(f"    Confidence: {prediction_response.confidence}")
        print(f"    Needs Review: {prediction_response.needs_manual_review}")
        print()
    
    print(f"  Total processed: {len(predictions)}")
    print(f"  High confidence: {high_confidence_count}")
    print(f"  Needs review: {needs_review_count}")
    print()
    
    # Test model info
    print("3. Testing model information:")
    model_info = service.get_model_info()
    print(f"  Model loaded: {model_info['model_loaded']}")
    print(f"  Model version: {model_info['model_version']}")
    print(f"  Confidence threshold: {model_info['min_confidence_threshold']}")
    print(f"  Categories count: {model_info['categories_count']}")
    print()
    
    # Test feature extraction with various transaction types
    print("4. Testing feature extraction with various transactions:")
    test_transactions = [
        {
            'description': 'AMAZON.COM AMZN.COM/BILL WA',
            'amount': -89.99,
            'transaction_type': 'expense',
            'date': datetime(2024, 1, 20)
        },
        {
            'description': 'PAYCHECK DEPOSIT',
            'amount': 2500.00,
            'transaction_type': 'income',
            'date': datetime(2024, 1, 15)
        },
        {
            'description': 'TRANSFER TO SAVINGS',
            'amount': -500.00,
            'transaction_type': 'transfer',
            'date': datetime(2024, 1, 18)
        }
    ]
    
    features_df = service._extract_features(test_transactions)
    print(f"  Features extracted for {len(test_transactions)} transactions:")
    for i, trans in enumerate(test_transactions):
        print(f"    Transaction {i+1}: {trans['description'][:30]}...")
        print(f"      Processed: {features_df.iloc[i]['description_processed']}")
        print(f"      Amount range: {features_df.iloc[i]['amount_range']}")
        print(f"      Type: {features_df.iloc[i]['transaction_type']}")
        print()
    
    print("ML Categorization Integration test completed successfully!")
    print("\nNext steps:")
    print("- Train a model with actual categorized transaction data")
    print("- Test prediction accuracy with real data")
    print("- Implement model retraining workflow")
    print("- Add more sophisticated feature engineering")


if __name__ == "__main__":
    test_categorization_integration()