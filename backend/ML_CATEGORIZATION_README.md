# ML Categorization System

## Overview

The ML Categorization System provides automated transaction categorization using machine learning. It includes training, prediction, confidence scoring, and model retraining capabilities.

## Features

### Core Functionality
- **Automated Categorization**: Uses scikit-learn Random Forest classifier to predict transaction categories
- **Text Processing**: Advanced NLP preprocessing with NLTK for transaction descriptions
- **Confidence Scoring**: Provides confidence scores for predictions to identify uncertain categorizations
- **Manual Corrections**: Learns from user corrections to improve future predictions
- **Model Retraining**: Supports periodic retraining with updated data

### API Endpoints

#### Prediction Endpoints
- `POST /api/categorization/predict` - Single transaction prediction
- `POST /api/categorization/predict/bulk` - Bulk transaction predictions
- `POST /api/categorization/auto-categorize/{transaction_id}` - Auto-categorize specific transaction

#### Training Endpoints
- `POST /api/categorization/train` - Train new model
- `POST /api/categorization/retrain` - Retrain existing model

#### Correction & Feedback
- `POST /api/categorization/correct` - Provide manual correction feedback

#### Information & Statistics
- `GET /api/categorization/model/info` - Get model information
- `GET /api/categorization/stats` - Get categorization statistics

## Technical Architecture

### ML Pipeline Components

1. **Text Preprocessing**
   - Lowercase conversion
   - Special character removal
   - Number tokenization (replaced with 'NUM')
   - Stop word removal
   - Stemming with Porter Stemmer

2. **Feature Engineering**
   - Processed transaction descriptions (TF-IDF vectorization)
   - Amount ranges (very_small, small, medium, large, very_large)
   - Date features (month, day of week, weekend indicator)
   - Transaction type

3. **Model Architecture**
   - Random Forest Classifier (100 estimators)
   - TF-IDF Vectorizer (max 1000 features, 1-2 ngrams)
   - Cross-validation for model evaluation

### Data Models

#### Core Schemas
- `PredictionRequest` - Input for predictions
- `PredictionResponse` - Prediction results with confidence
- `BulkPredictionRequest/Response` - Bulk operations
- `CorrectionRequest/Response` - Manual corrections
- `TrainingRequest/Response` - Model training
- `ModelInfoResponse` - Model status information
- `CategorizationStats` - Performance statistics

## Installation & Setup

### Dependencies
```bash
uv pip install scikit-learn==1.4.0 joblib==1.3.2 numpy==1.26.3 nltk==3.8.1
```

### NLTK Data
The system automatically downloads required NLTK data:
- punkt tokenizer
- stopwords corpus

### Model Storage
Models are stored in the `models/` directory:
- `categorization_model_{version}.joblib` - Trained pipeline
- `label_encoder_{version}.joblib` - Category label encoder
- `current_model.txt` - Current model version
- `corrections.log` - Manual correction log

## Usage Examples

### Single Prediction
```python
from app.services.ml_categorization import ml_categorization_service

prediction = ml_categorization_service.predict_category(
    description="WALMART SUPERCENTER",
    amount=-45.67,
    transaction_type="expense"
)

print(f"Category: {prediction['predicted_category']}")
print(f"Confidence: {prediction['confidence']}")
print(f"Needs Review: {prediction['needs_manual_review']}")
```

### API Usage
```bash
# Single prediction
curl -X POST "/api/categorization/predict" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "WALMART SUPERCENTER",
    "amount": -45.67,
    "transaction_type": "expense"
  }'

# Bulk predictions
curl -X POST "/api/categorization/predict/bulk" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "transactions": [
      {
        "description": "WALMART SUPERCENTER",
        "amount": -45.67,
        "transaction_type": "expense"
      },
      {
        "description": "SHELL GAS STATION",
        "amount": -32.50,
        "transaction_type": "expense"
      }
    ]
  }'
```

### Training a Model
```bash
curl -X POST "/api/categorization/train" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user-uuid",
    "force_retrain": false
  }'
```

## Performance Considerations

### Training Requirements
- Minimum 10 categorized transactions required
- Recommended 100+ transactions for good accuracy
- Cross-validation used for model evaluation

### Prediction Performance
- Fast inference (< 100ms for single prediction)
- Batch processing supported for bulk operations
- Confidence threshold: 0.6 (configurable)

### Model Accuracy
- Target accuracy: 85%+ for recurring transaction types
- Confidence scoring helps identify uncertain predictions
- Continuous learning from manual corrections

## Configuration

### Service Configuration
```python
class MLCategorizationService:
    min_confidence_threshold = 0.6  # Minimum confidence for auto-categorization
    model_path = Path("models")     # Model storage directory
```

### Model Parameters
```python
# Random Forest Classifier
n_estimators=100
max_depth=10
min_samples_split=5
min_samples_leaf=2

# TF-IDF Vectorizer
max_features=1000
ngram_range=(1, 2)
min_df=2
max_df=0.8
```

## Testing

### Unit Tests
```bash
uv run python -m pytest tests/test_ml_categorization.py -v
```

### Integration Tests
```bash
uv run python test_categorization_integration.py
```

### API Tests
```bash
uv run python test_api_endpoints.py
```

### Demo Script
```bash
uv run python test_ml_categorization_demo.py
```

## Monitoring & Maintenance

### Model Performance Metrics
- Accuracy on test set
- Cross-validation scores
- Confidence score distribution
- Manual correction rate

### Retraining Triggers
- Number of manual corrections threshold
- Time-based retraining schedule
- Accuracy degradation detection
- New category additions

### Logging & Debugging
- Correction logs for model improvement
- Prediction confidence tracking
- Error logging for failed predictions
- Performance metrics collection

## Future Enhancements

### Planned Features
1. **Advanced Feature Engineering**
   - Merchant name extraction
   - Amount pattern recognition
   - Seasonal categorization patterns

2. **Model Improvements**
   - Ensemble methods (Random Forest + Gradient Boosting)
   - Deep learning models for text classification
   - Active learning for uncertain predictions

3. **User Experience**
   - Confidence-based UI indicators
   - Batch correction workflows
   - Category suggestion improvements

4. **Performance Optimization**
   - Model caching strategies
   - Incremental learning
   - Distributed training for large datasets

### Integration Opportunities
- Bank transaction import automation
- Receipt OCR categorization
- Expense report generation
- Tax deduction identification

## Troubleshooting

### Common Issues

1. **Model Not Loading**
   - Check model files exist in models/ directory
   - Verify file permissions
   - Check NLTK data download

2. **Low Prediction Accuracy**
   - Increase training data size
   - Review category consistency
   - Adjust confidence threshold

3. **Training Failures**
   - Ensure minimum 10 categorized transactions
   - Check for data quality issues
   - Verify category distribution

4. **API Authentication Errors**
   - Verify JWT token validity
   - Check user permissions
   - Ensure proper headers

### Debug Commands
```bash
# Check model status
curl -X GET "/api/categorization/model/info" -H "Authorization: Bearer {token}"

# Get categorization statistics
curl -X GET "/api/categorization/stats" -H "Authorization: Bearer {token}"

# Test basic functionality
uv run python test_ml_categorization_demo.py
```

## Security Considerations

- All endpoints require authentication
- User data isolation (models trained per user)
- Secure model file storage
- Input validation and sanitization
- Rate limiting on training endpoints

## Performance Benchmarks

- Single prediction: < 100ms
- Bulk prediction (100 transactions): < 2s
- Model training (1000 transactions): < 30s
- Model loading: < 1s

This ML categorization system provides a robust foundation for automated transaction categorization with room for future enhancements and optimizations.