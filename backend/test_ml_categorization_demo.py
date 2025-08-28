#!/usr/bin/env python3
"""
Demo script to test ML categorization functionality
"""

import sys
import os
from pathlib import Path

# Add the app directory to Python path
sys.path.append(str(Path(__file__).parent))

from app.services.ml_categorization import MLCategorizationService
from datetime import datetime


def test_ml_categorization():
    """Test ML categorization service functionality"""
    print("Testing ML Categorization Service")
    print("=" * 50)
    
    # Initialize service
    service = MLCategorizationService()
    
    # Test text preprocessing
    print("\n1. Testing text preprocessing:")
    test_descriptions = [
        "WALMART SUPERCENTER #1234",
        "SHELL GAS STATION 123 MAIN ST",
        "MCDONALD'S #5678 DRIVE THRU",
        "AMAZON.COM AMZN.COM/BILL WA",
        "ATM WITHDRAWAL 123456"
    ]
    
    for desc in test_descriptions:
        processed = service._preprocess_text(desc)
        print(f"  Original: {desc}")
        print(f"  Processed: {processed}")
        print()
    
    # Test feature extraction
    print("2. Testing feature extraction:")
    sample_transactions = [
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
        }
    ]
    
    features_df = service._extract_features(sample_transactions)
    print(f"  Features extracted: {list(features_df.columns)}")
    print(f"  Number of transactions: {len(features_df)}")
    print(f"  Sample features:")
    for col in features_df.columns:
        print(f"    {col}: {features_df[col].iloc[0]}")
    print()
    
    # Test amount ranges
    print("3. Testing amount ranges:")
    test_amounts = [5.0, 25.0, 100.0, 500.0, 2000.0]
    for amount in test_amounts:
        range_cat = service._get_amount_range(amount)
        print(f"  ${amount} -> {range_cat}")
    print()
    
    # Test prediction without model (should return no prediction)
    print("4. Testing prediction without trained model:")
    prediction = service.predict_category(
        description="WALMART SUPERCENTER",
        amount=45.67
    )
    print(f"  Prediction: {prediction}")
    print()
    
    # Test model info
    print("5. Testing model info:")
    model_info = service.get_model_info()
    print(f"  Model info: {model_info}")
    print()
    
    print("ML Categorization Service test completed successfully!")
    print("Note: Full training and prediction testing requires a database with categorized transactions.")


if __name__ == "__main__":
    test_ml_categorization()