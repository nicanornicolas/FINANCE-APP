"""
Categorization API endpoints for ML-based transaction categorization
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from ...db.database import get_db
from ...services.ml_categorization import ml_categorization_service
from ...services.rule_based_categorization import rule_based_categorization_service
from ...schemas.categorization import (
    PredictionRequest, PredictionResponse,
    BulkPredictionRequest, BulkPredictionResponse,
    CorrectionRequest, CorrectionResponse,
    TrainingRequest, TrainingResponse,
    ModelInfoResponse, CategorizationStats
)
from ...models.transaction import Transaction
from ...models.category import Category
from ...models.user import User
from ..dependencies import get_current_user

router = APIRouter(prefix="/categorization", tags=["categorization"])


@router.post("/predict", response_model=PredictionResponse)
async def predict_category(
    request: PredictionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Predict category for a single transaction using ML model
    """
    try:
        prediction = ml_categorization_service.predict_category(
            description=request.description,
            amount=request.amount,
            transaction_type=request.transaction_type,
            date=request.date
        )
        
        return PredictionResponse(**prediction)
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prediction failed: {str(e)}"
        )


@router.post("/predict/bulk", response_model=BulkPredictionResponse)
async def predict_categories_bulk(
    request: BulkPredictionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Predict categories for multiple transactions in bulk
    """
    try:
        predictions = []
        high_confidence_count = 0
        needs_review_count = 0
        
        for transaction_request in request.transactions:
            prediction = ml_categorization_service.predict_category(
                description=transaction_request.description,
                amount=transaction_request.amount,
                transaction_type=transaction_request.transaction_type,
                date=transaction_request.date
            )
            
            prediction_response = PredictionResponse(**prediction)
            predictions.append(prediction_response)
            
            if prediction_response.needs_manual_review:
                needs_review_count += 1
            else:
                high_confidence_count += 1
        
        return BulkPredictionResponse(
            predictions=predictions,
            total_processed=len(predictions),
            high_confidence_count=high_confidence_count,
            needs_review_count=needs_review_count
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Bulk prediction failed: {str(e)}"
        )


@router.post("/correct", response_model=CorrectionResponse)
async def correct_categorization(
    request: CorrectionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Provide manual correction for a transaction categorization
    """
    try:
        # Verify transaction belongs to current user
        transaction = db.query(Transaction).filter(Transaction.id == request.transaction_id).first()
        if not transaction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transaction not found"
            )
        
        # Verify transaction belongs to user's account
        from ...models.account import Account
        account = db.query(Account).filter(Account.id == transaction.account_id).first()
        if not account or account.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Transaction does not belong to current user"
            )
        
        # Verify category belongs to current user
        category = db.query(Category).filter(Category.id == request.correct_category_id).first()
        if not category or category.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Category does not belong to current user"
            )
        
        # Update model with correction
        correction_result = ml_categorization_service.update_model_with_correction(
            db=db,
            transaction_id=str(request.transaction_id),
            correct_category_id=str(request.correct_category_id)
        )
        
        return CorrectionResponse(
            status=correction_result['status'],
            transaction_id=request.transaction_id,
            correct_category=correction_result['correct_category']
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Correction failed: {str(e)}"
        )


@router.post("/train", response_model=TrainingResponse)
async def train_model(
    request: TrainingRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Train or retrain the ML categorization model
    """
    try:
        # Use current user's ID if not specified
        user_id = str(request.user_id) if request.user_id else str(current_user.id)
        
        # Check if user has sufficient categorized transactions
        from ...models.account import Account
        user_accounts = db.query(Account).filter(Account.user_id == user_id).all()
        account_ids = [acc.id for acc in user_accounts]
        
        categorized_count = db.query(Transaction).filter(
            Transaction.account_id.in_(account_ids),
            Transaction.category_id.isnot(None)
        ).count()
        
        if categorized_count < 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient training data. Need at least 10 categorized transactions, found {categorized_count}"
            )
        
        # Train model (this might take a while, so we could run it in background)
        training_result = ml_categorization_service.train_model(db=db, user_id=user_id)
        
        return TrainingResponse(**training_result)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Training failed: {str(e)}"
        )


@router.post("/retrain", response_model=TrainingResponse)
async def retrain_model(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrain the ML model with updated data
    """
    try:
        training_result = ml_categorization_service.retrain_model(
            db=db, 
            user_id=str(current_user.id)
        )
        
        return TrainingResponse(**training_result)
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Retraining failed: {str(e)}"
        )


@router.get("/model/info", response_model=ModelInfoResponse)
async def get_model_info(
    current_user: User = Depends(get_current_user)
):
    """
    Get information about the current ML model
    """
    try:
        model_info = ml_categorization_service.get_model_info()
        return ModelInfoResponse(**model_info)
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get model info: {str(e)}"
        )


@router.get("/stats", response_model=CategorizationStats)
async def get_categorization_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get statistics about categorization performance for current user
    """
    try:
        # Get user's accounts
        from ...models.account import Account
        user_accounts = db.query(Account).filter(Account.user_id == current_user.id).all()
        account_ids = [acc.id for acc in user_accounts]
        
        # Calculate statistics
        total_transactions = db.query(Transaction).filter(
            Transaction.account_id.in_(account_ids)
        ).count()
        
        categorized_transactions = db.query(Transaction).filter(
            Transaction.account_id.in_(account_ids),
            Transaction.category_id.isnot(None)
        ).count()
        
        auto_categorized = db.query(Transaction).filter(
            Transaction.account_id.in_(account_ids),
            Transaction.category_id.isnot(None),
            Transaction.confidence_score > 0.0,
            Transaction.confidence_score < 1.0
        ).count()
        
        manual_corrections = db.query(Transaction).filter(
            Transaction.account_id.in_(account_ids),
            Transaction.confidence_score == 1.0
        ).count()
        
        # Calculate average confidence for auto-categorized transactions
        confidence_query = db.query(Transaction.confidence_score).filter(
            Transaction.account_id.in_(account_ids),
            Transaction.category_id.isnot(None),
            Transaction.confidence_score > 0.0
        ).all()
        
        average_confidence = sum(c[0] for c in confidence_query) / len(confidence_query) if confidence_query else 0.0
        categorization_rate = (categorized_transactions / total_transactions * 100) if total_transactions > 0 else 0.0
        
        return CategorizationStats(
            total_transactions=total_transactions,
            categorized_transactions=categorized_transactions,
            auto_categorized=auto_categorized,
            manual_corrections=manual_corrections,
            average_confidence=average_confidence,
            categorization_rate=categorization_rate
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get categorization stats: {str(e)}"
        )


@router.post("/auto-categorize/{transaction_id}")
async def auto_categorize_transaction(
    transaction_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Auto-categorize a specific transaction using ML model
    """
    try:
        # Get transaction
        transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
        if not transaction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transaction not found"
            )
        
        # Verify transaction belongs to user
        from ...models.account import Account
        account = db.query(Account).filter(Account.id == transaction.account_id).first()
        if not account or account.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Transaction does not belong to current user"
            )
        
        # Get prediction
        prediction = ml_categorization_service.predict_category(
            description=transaction.description,
            amount=float(transaction.amount),
            transaction_type=transaction.transaction_type.value,
            date=transaction.date
        )
        
        # If confidence is high enough, auto-apply the categorization
        if not prediction['needs_manual_review'] and prediction['predicted_category']:
            # Find category by name for this user
            category = db.query(Category).filter(
                Category.user_id == current_user.id,
                Category.name == prediction['predicted_category']
            ).first()
            
            if category:
                transaction.category_id = category.id
                transaction.confidence_score = prediction['confidence']
                db.commit()
                
                return {
                    "status": "auto_categorized",
                    "category": prediction['predicted_category'],
                    "confidence": prediction['confidence']
                }
        
        return {
            "status": "needs_manual_review",
            "prediction": prediction
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Auto-categorization failed: {str(e)}"
        )


@router.post("/suggest")
async def suggest_categories(
    request: PredictionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get category suggestions using rule-based categorization
    """
    try:
        suggestions = rule_based_categorization_service.get_category_suggestions(
            description=request.description,
            amount=request.amount,
            transaction_type=request.transaction_type,
            db=db,
            user_id=current_user.id,
            limit=3
        )

        return {
            "suggestions": suggestions,
            "total_suggestions": len(suggestions)
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Category suggestion failed: {str(e)}"
        )


@router.post("/categorize-rules/{transaction_id}")
async def categorize_with_rules(
    transaction_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Categorize a transaction using rule-based categorization
    """
    try:
        # Get transaction
        transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
        if not transaction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transaction not found"
            )

        # Verify transaction belongs to user
        from ...models.account import Account
        account = db.query(Account).filter(Account.id == transaction.account_id).first()
        if not account or account.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Transaction does not belong to current user"
            )

        # Get rule-based categorization
        result = rule_based_categorization_service.categorize_transaction(
            description=transaction.description,
            amount=float(transaction.amount),
            transaction_type=transaction.transaction_type
        )

        if result:
            category_name, confidence, rule_name = result

            # Find category by name for this user
            category = db.query(Category).filter(
                Category.user_id == current_user.id,
                Category.name == category_name
            ).first()

            if category:
                transaction.category_id = category.id
                transaction.confidence_score = confidence / 100.0  # Convert to decimal
                db.commit()

                return {
                    "status": "categorized",
                    "category": category_name,
                    "confidence": confidence,
                    "rule_name": rule_name,
                    "method": "rule_based"
                }

        return {
            "status": "no_match",
            "message": "No matching rule found for this transaction"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Rule-based categorization failed: {str(e)}"
        )