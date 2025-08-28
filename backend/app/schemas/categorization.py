"""
Categorization schemas for ML-based transaction categorization
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID


class CategoryPrediction(BaseModel):
    """Single category prediction with confidence"""
    category: str
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score between 0 and 1")


class PredictionRequest(BaseModel):
    """Request for category prediction"""
    description: str = Field(..., min_length=1, description="Transaction description")
    amount: float = Field(..., description="Transaction amount")
    transaction_type: str = Field(default="expense", description="Transaction type")
    date: Optional[datetime] = Field(default=None, description="Transaction date")


class PredictionResponse(BaseModel):
    """Response from category prediction"""
    predicted_category: Optional[str] = Field(None, description="Most likely category")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in prediction")
    all_predictions: List[CategoryPrediction] = Field(default=[], description="Top 3 predictions")
    needs_manual_review: bool = Field(..., description="Whether manual review is recommended")


class CorrectionRequest(BaseModel):
    """Request to correct a categorization"""
    transaction_id: UUID = Field(..., description="Transaction ID to correct")
    correct_category_id: UUID = Field(..., description="Correct category ID")


class CorrectionResponse(BaseModel):
    """Response from categorization correction"""
    status: str = Field(..., description="Status of the correction")
    transaction_id: UUID = Field(..., description="Transaction ID that was corrected")
    correct_category: str = Field(..., description="Name of the correct category")


class TrainingRequest(BaseModel):
    """Request to train/retrain the model"""
    user_id: Optional[UUID] = Field(None, description="User ID to train model for (optional)")
    force_retrain: bool = Field(default=False, description="Force retraining even if model exists")


class TrainingResponse(BaseModel):
    """Response from model training"""
    accuracy: float = Field(..., ge=0.0, le=1.0, description="Model accuracy on test set")
    cv_mean: float = Field(..., ge=0.0, le=1.0, description="Cross-validation mean score")
    cv_std: float = Field(..., ge=0.0, description="Cross-validation standard deviation")
    training_samples: int = Field(..., ge=0, description="Number of training samples used")
    unique_categories: int = Field(..., ge=0, description="Number of unique categories")
    model_version: str = Field(..., description="Version identifier of the trained model")


class ModelInfoResponse(BaseModel):
    """Information about the current model"""
    model_loaded: bool = Field(..., description="Whether a model is currently loaded")
    model_version: Optional[str] = Field(None, description="Current model version")
    min_confidence_threshold: float = Field(..., description="Minimum confidence threshold")
    categories_count: int = Field(..., description="Number of categories the model can predict")


class BulkPredictionRequest(BaseModel):
    """Request for bulk category predictions"""
    transactions: List[PredictionRequest] = Field(..., min_items=1, max_items=100)


class BulkPredictionResponse(BaseModel):
    """Response from bulk category predictions"""
    predictions: List[PredictionResponse] = Field(..., description="Predictions for each transaction")
    total_processed: int = Field(..., description="Total number of transactions processed")
    high_confidence_count: int = Field(..., description="Number of high-confidence predictions")
    needs_review_count: int = Field(..., description="Number of predictions needing manual review")


class CategorizationStats(BaseModel):
    """Statistics about categorization performance"""
    total_transactions: int = Field(..., description="Total transactions in system")
    categorized_transactions: int = Field(..., description="Number of categorized transactions")
    auto_categorized: int = Field(..., description="Number of auto-categorized transactions")
    manual_corrections: int = Field(..., description="Number of manual corrections")
    average_confidence: float = Field(..., description="Average confidence score")
    categorization_rate: float = Field(..., description="Percentage of transactions categorized")


class RetrainingTrigger(BaseModel):
    """Trigger for model retraining"""
    trigger_type: str = Field(..., description="Type of trigger (manual, scheduled, threshold)")
    threshold_met: Optional[str] = Field(None, description="Which threshold was met")
    corrections_since_last_training: Optional[int] = Field(None, description="Number of corrections")
    last_training_date: Optional[datetime] = Field(None, description="Date of last training")