"""
Machine Learning Categorization Service

This service provides ML-based transaction categorization using scikit-learn.
It includes training, prediction, confidence scoring, and model retraining capabilities.
"""

import os
import re
import joblib
import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional
from datetime import datetime
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, accuracy_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import PorterStemmer

from sqlalchemy.orm import Session
from ..models.transaction import Transaction
from ..models.category import Category
from ..core.config import settings


class MLCategorizationService:
    """ML-based transaction categorization service"""
    
    def __init__(self):
        self.model_path = Path("models")
        self.model_path.mkdir(exist_ok=True)
        
        # Initialize NLTK components
        self._download_nltk_data()
        self.stemmer = PorterStemmer()
        self.stop_words = set(stopwords.words('english'))
        
        # Model components
        self.pipeline = None
        self.label_encoder = None
        self.feature_names = []
        self.model_version = None
        self.min_confidence_threshold = 0.6
        
        # Load existing model if available
        self._load_model()
    
    def _download_nltk_data(self):
        """Download required NLTK data"""
        try:
            nltk.data.find('tokenizers/punkt')
            nltk.data.find('corpora/stopwords')
        except LookupError:
            nltk.download('punkt', quiet=True)
            nltk.download('stopwords', quiet=True)
    
    def _preprocess_text(self, text: str) -> str:
        """Preprocess transaction description text"""
        if not text:
            return ""
        
        # Convert to lowercase
        text = text.lower()
        
        # Remove special characters and numbers (keep some context)
        text = re.sub(r'[^\w\s]', ' ', text)
        text = re.sub(r'\d+', 'NUM', text)  # Replace numbers with NUM token
        
        # Tokenize and remove stopwords
        tokens = word_tokenize(text)
        tokens = [self.stemmer.stem(token) for token in tokens 
                 if token not in self.stop_words and len(token) > 2]
        
        return ' '.join(tokens)
    
    def _extract_features(self, transactions: List[Dict]) -> pd.DataFrame:
        """Extract features from transactions for ML training"""
        features = []
        
        for trans in transactions:
            # Text features
            processed_desc = self._preprocess_text(trans['description'])
            
            # Amount features
            amount = float(trans['amount'])
            amount_range = self._get_amount_range(amount)
            
            # Date features (if available)
            date_features = {}
            if 'date' in trans and trans['date']:
                if isinstance(trans['date'], str):
                    date_obj = datetime.fromisoformat(trans['date'].replace('Z', '+00:00'))
                else:
                    date_obj = trans['date']
                
                date_features = {
                    'month': date_obj.month,
                    'day_of_week': date_obj.weekday(),
                    'is_weekend': date_obj.weekday() >= 5
                }
            
            feature_dict = {
                'description_processed': processed_desc,
                'amount': amount,
                'amount_range': amount_range,
                'transaction_type': trans.get('transaction_type', 'expense'),
                **date_features
            }
            
            features.append(feature_dict)
        
        return pd.DataFrame(features)
    
    def _get_amount_range(self, amount: float) -> str:
        """Categorize amount into ranges"""
        abs_amount = abs(amount)
        if abs_amount < 10:
            return 'very_small'
        elif abs_amount < 50:
            return 'small'
        elif abs_amount < 200:
            return 'medium'
        elif abs_amount < 1000:
            return 'large'
        else:
            return 'very_large'
    
    def train_model(self, db: Session, user_id: Optional[str] = None) -> Dict:
        """Train the ML categorization model"""
        # Fetch training data
        query = db.query(Transaction).filter(Transaction.category_id.isnot(None))
        if user_id:
            # Filter by user's accounts if user_id provided
            from ..models.account import Account
            user_accounts = db.query(Account).filter(Account.user_id == user_id).all()
            account_ids = [acc.id for acc in user_accounts]
            query = query.filter(Transaction.account_id.in_(account_ids))
        
        transactions = query.all()
        
        if len(transactions) < 10:
            raise ValueError("Insufficient training data. Need at least 10 categorized transactions.")
        
        # Prepare training data
        training_data = []
        labels = []
        
        for trans in transactions:
            category = db.query(Category).filter(Category.id == trans.category_id).first()
            if category:
                training_data.append({
                    'description': trans.description,
                    'amount': float(trans.amount),
                    'transaction_type': trans.transaction_type.value,
                    'date': trans.date
                })
                labels.append(category.name)
        
        # Extract features
        features_df = self._extract_features(training_data)
        
        # Prepare labels
        self.label_encoder = LabelEncoder()
        encoded_labels = self.label_encoder.fit_transform(labels)
        
        # Create pipeline
        self.pipeline = Pipeline([
            ('tfidf', TfidfVectorizer(
                max_features=1000,
                ngram_range=(1, 2),
                min_df=2,
                max_df=0.8
            )),
            ('classifier', RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                min_samples_split=5,
                min_samples_leaf=2,
                random_state=42
            ))
        ])
        
        # Combine text and numerical features
        X_text = features_df['description_processed'].fillna('')
        X_numerical = features_df[['amount', 'month', 'day_of_week']].fillna(0)
        
        # For now, use only text features (can be enhanced later)
        X = X_text
        y = encoded_labels
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # Train model
        self.pipeline.fit(X_train, y_train)
        
        # Evaluate model
        y_pred = self.pipeline.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        
        # Cross-validation score
        cv_scores = cross_val_score(self.pipeline, X, y, cv=5)
        
        # Save model
        self.model_version = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._save_model()
        
        return {
            'accuracy': accuracy,
            'cv_mean': cv_scores.mean(),
            'cv_std': cv_scores.std(),
            'training_samples': len(training_data),
            'unique_categories': len(set(labels)),
            'model_version': self.model_version
        }
    
    def predict_category(self, description: str, amount: float, 
                        transaction_type: str = 'expense',
                        date: Optional[datetime] = None) -> Dict:
        """Predict category for a transaction"""
        if not self.pipeline or not self.label_encoder:
            return {
                'predicted_category': None,
                'confidence': 0.0,
                'all_predictions': [],
                'needs_manual_review': True
            }
        
        # Prepare features
        transaction_data = [{
            'description': description,
            'amount': amount,
            'transaction_type': transaction_type,
            'date': date or datetime.now()
        }]
        
        features_df = self._extract_features(transaction_data)
        X_text = features_df['description_processed'].fillna('')
        
        # Get prediction probabilities
        probabilities = self.pipeline.predict_proba(X_text)[0]
        predicted_class_idx = np.argmax(probabilities)
        confidence = probabilities[predicted_class_idx]
        
        # Get category name
        predicted_category = self.label_encoder.inverse_transform([predicted_class_idx])[0]
        
        # Get top 3 predictions
        top_indices = np.argsort(probabilities)[-3:][::-1]
        all_predictions = [
            {
                'category': self.label_encoder.inverse_transform([idx])[0],
                'confidence': float(probabilities[idx])
            }
            for idx in top_indices
        ]
        
        return {
            'predicted_category': predicted_category,
            'confidence': float(confidence),
            'all_predictions': all_predictions,
            'needs_manual_review': confidence < self.min_confidence_threshold
        }
    
    def update_model_with_correction(self, db: Session, transaction_id: str, 
                                   correct_category_id: str) -> Dict:
        """Update model with manual correction feedback"""
        # This is a simplified approach - in production, you'd want more sophisticated
        # online learning or periodic retraining
        
        transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
        if not transaction:
            raise ValueError("Transaction not found")
        
        category = db.query(Category).filter(Category.id == correct_category_id).first()
        if not category:
            raise ValueError("Category not found")
        
        # Update transaction with correct category and high confidence
        transaction.category_id = correct_category_id
        transaction.confidence_score = 1.0  # Manual correction = 100% confidence
        db.commit()
        
        # Log correction for future retraining
        correction_log = {
            'timestamp': datetime.now().isoformat(),
            'transaction_id': str(transaction_id),
            'description': transaction.description,
            'amount': float(transaction.amount),
            'correct_category': category.name,
            'model_version': self.model_version
        }
        
        # Save correction log (in production, use proper logging/database)
        log_file = self.model_path / "corrections.log"
        with open(log_file, "a") as f:
            f.write(f"{correction_log}\n")
        
        return {
            'status': 'correction_recorded',
            'transaction_id': str(transaction_id),
            'correct_category': category.name
        }
    
    def retrain_model(self, db: Session, user_id: Optional[str] = None) -> Dict:
        """Retrain the model with updated data"""
        return self.train_model(db, user_id)
    
    def get_model_info(self) -> Dict:
        """Get information about the current model"""
        return {
            'model_loaded': self.pipeline is not None,
            'model_version': self.model_version,
            'min_confidence_threshold': self.min_confidence_threshold,
            'categories_count': len(self.label_encoder.classes_) if self.label_encoder else 0
        }
    
    def _save_model(self):
        """Save the trained model to disk"""
        if self.pipeline and self.label_encoder:
            model_file = self.model_path / f"categorization_model_{self.model_version}.joblib"
            encoder_file = self.model_path / f"label_encoder_{self.model_version}.joblib"
            
            joblib.dump(self.pipeline, model_file)
            joblib.dump(self.label_encoder, encoder_file)
            
            # Save current model info
            info_file = self.model_path / "current_model.txt"
            with open(info_file, "w") as f:
                f.write(self.model_version)
    
    def _load_model(self):
        """Load the most recent trained model"""
        try:
            info_file = self.model_path / "current_model.txt"
            if info_file.exists():
                with open(info_file, "r") as f:
                    self.model_version = f.read().strip()
                
                model_file = self.model_path / f"categorization_model_{self.model_version}.joblib"
                encoder_file = self.model_path / f"label_encoder_{self.model_version}.joblib"
                
                if model_file.exists() and encoder_file.exists():
                    self.pipeline = joblib.load(model_file)
                    self.label_encoder = joblib.load(encoder_file)
        except Exception as e:
            print(f"Could not load existing model: {e}")
            self.pipeline = None
            self.label_encoder = None
            self.model_version = None


# Global instance
ml_categorization_service = MLCategorizationService()