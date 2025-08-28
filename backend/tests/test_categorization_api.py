"""
Tests for categorization API endpoints
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from uuid import uuid4
from datetime import datetime

from app.main import app
from app.schemas.categorization import (
    PredictionResponse, BulkPredictionResponse, 
    CorrectionResponse, TrainingResponse, ModelInfoResponse
)


class TestCategorizationAPI:
    """Test categorization API endpoints"""
    
    @pytest.fixture
    def client(self):
        """Test client"""
        return TestClient(app)
    
    @pytest.fixture
    def mock_current_user(self):
        """Mock current user"""
        user = Mock()
        user.id = uuid4()
        user.email = "test@example.com"
        return user
    
    @pytest.fixture
    def auth_headers(self):
        """Mock authentication headers"""
        return {"Authorization": "Bearer test_token"}
    
    @patch('app.api.routers.categorization.get_current_user')
    @patch('app.api.routers.categorization.ml_categorization_service')
    def test_predict_category_success(self, mock_ml_service, mock_get_user, 
                                    client, mock_current_user, auth_headers):
        """Test successful category prediction"""
        mock_get_user.return_value = mock_current_user
        mock_ml_service.predict_category.return_value = {
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
        
        response = client.post(
            '/api/categorization/predict',
            json=request_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['predicted_category'] == 'Groceries'
        assert data['confidence'] == 0.85
        assert data['needs_manual_review'] is False
        assert len(data['all_predictions']) == 3
    
    @patch('app.api.routers.categorization.get_current_user')
    @patch('app.api.routers.categorization.ml_categorization_service')
    def test_predict_category_error(self, mock_ml_service, mock_get_user,
                                  client, mock_current_user, auth_headers):
        """Test prediction error handling"""
        mock_get_user.return_value = mock_current_user
        mock_ml_service.predict_category.side_effect = Exception("Model error")
        
        request_data = {
            'description': 'TEST TRANSACTION',
            'amount': -50.0
        }
        
        response = client.post(
            '/api/categorization/predict',
            json=request_data,
            headers=auth_headers
        )
        
        assert response.status_code == 500
        assert 'Prediction failed' in response.json()['detail']
    
    @patch('app.api.routers.categorization.get_current_user')
    @patch('app.api.routers.categorization.ml_categorization_service')
    def test_bulk_predict_success(self, mock_ml_service, mock_get_user,
                                client, mock_current_user, auth_headers):
        """Test bulk prediction success"""
        mock_get_user.return_value = mock_current_user
        mock_ml_service.predict_category.return_value = {
            'predicted_category': 'Groceries',
            'confidence': 0.85,
            'all_predictions': [{'category': 'Groceries', 'confidence': 0.85}],
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
        
        response = client.post(
            '/api/categorization/predict/bulk',
            json=request_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['total_processed'] == 2
        assert data['high_confidence_count'] == 2
        assert data['needs_review_count'] == 0
        assert len(data['predictions']) == 2
    
    @patch('app.api.routers.categorization.get_current_user')
    @patch('app.api.routers.categorization.get_db')
    @patch('app.api.routers.categorization.ml_categorization_service')
    def test_correct_categorization_success(self, mock_ml_service, mock_get_db,
                                          mock_get_user, client, mock_current_user, auth_headers):
        """Test successful categorization correction"""
        mock_get_user.return_value = mock_current_user
        
        # Mock database objects
        mock_transaction = Mock()
        mock_transaction.id = uuid4()
        mock_transaction.account_id = uuid4()
        
        mock_account = Mock()
        mock_account.id = mock_transaction.account_id
        mock_account.user_id = mock_current_user.id
        
        mock_category = Mock()
        mock_category.id = uuid4()
        mock_category.user_id = mock_current_user.id
        mock_category.name = "Corrected Category"
        
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_transaction, mock_account, mock_category
        ]
        mock_get_db.return_value = mock_db
        
        mock_ml_service.update_model_with_correction.return_value = {
            'status': 'correction_recorded',
            'transaction_id': str(mock_transaction.id),
            'correct_category': mock_category.name
        }
        
        request_data = {
            'transaction_id': str(mock_transaction.id),
            'correct_category_id': str(mock_category.id)
        }
        
        response = client.post(
            '/api/categorization/correct',
            json=request_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'correction_recorded'
        assert data['correct_category'] == mock_category.name
    
    @patch('app.api.routers.categorization.get_current_user')
    @patch('app.api.routers.categorization.get_db')
    def test_correct_categorization_transaction_not_found(self, mock_get_db, mock_get_user,
                                                        client, mock_current_user, auth_headers):
        """Test correction with non-existent transaction"""
        mock_get_user.return_value = mock_current_user
        
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_get_db.return_value = mock_db
        
        request_data = {
            'transaction_id': str(uuid4()),
            'correct_category_id': str(uuid4())
        }
        
        response = client.post(
            '/api/categorization/correct',
            json=request_data,
            headers=auth_headers
        )
        
        assert response.status_code == 404
        assert 'Transaction not found' in response.json()['detail']
    
    @patch('app.api.routers.categorization.get_current_user')
    @patch('app.api.routers.categorization.get_db')
    @patch('app.api.routers.categorization.ml_categorization_service')
    def test_train_model_success(self, mock_ml_service, mock_get_db, mock_get_user,
                                client, mock_current_user, auth_headers):
        """Test successful model training"""
        mock_get_user.return_value = mock_current_user
        
        # Mock sufficient training data
        mock_db = Mock()
        mock_accounts = [Mock(id=uuid4())]
        mock_db.query.return_value.filter.return_value.all.return_value = mock_accounts
        mock_db.query.return_value.filter.return_value.count.return_value = 15
        mock_get_db.return_value = mock_db
        
        mock_ml_service.train_model.return_value = {
            'accuracy': 0.85,
            'cv_mean': 0.82,
            'cv_std': 0.03,
            'training_samples': 15,
            'unique_categories': 5,
            'model_version': '20240115_120000'
        }
        
        request_data = {
            'user_id': str(mock_current_user.id),
            'force_retrain': False
        }
        
        response = client.post(
            '/api/categorization/train',
            json=request_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['accuracy'] == 0.85
        assert data['training_samples'] == 15
        assert data['unique_categories'] == 5
    
    @patch('app.api.routers.categorization.get_current_user')
    @patch('app.api.routers.categorization.get_db')
    def test_train_model_insufficient_data(self, mock_get_db, mock_get_user,
                                         client, mock_current_user, auth_headers):
        """Test training with insufficient data"""
        mock_get_user.return_value = mock_current_user
        
        # Mock insufficient training data
        mock_db = Mock()
        mock_accounts = [Mock(id=uuid4())]
        mock_db.query.return_value.filter.return_value.all.return_value = mock_accounts
        mock_db.query.return_value.filter.return_value.count.return_value = 5  # Less than 10
        mock_get_db.return_value = mock_db
        
        request_data = {
            'user_id': str(mock_current_user.id)
        }
        
        response = client.post(
            '/api/categorization/train',
            json=request_data,
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert 'Insufficient training data' in response.json()['detail']
    
    @patch('app.api.routers.categorization.get_current_user')
    @patch('app.api.routers.categorization.ml_categorization_service')
    def test_get_model_info(self, mock_ml_service, mock_get_user,
                           client, mock_current_user, auth_headers):
        """Test getting model information"""
        mock_get_user.return_value = mock_current_user
        mock_ml_service.get_model_info.return_value = {
            'model_loaded': True,
            'model_version': '20240115_120000',
            'min_confidence_threshold': 0.6,
            'categories_count': 5
        }
        
        response = client.get(
            '/api/categorization/model/info',
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['model_loaded'] is True
        assert data['model_version'] == '20240115_120000'
        assert data['categories_count'] == 5
    
    @patch('app.api.routers.categorization.get_current_user')
    @patch('app.api.routers.categorization.get_db')
    def test_get_categorization_stats(self, mock_get_db, mock_get_user,
                                    client, mock_current_user, auth_headers):
        """Test getting categorization statistics"""
        mock_get_user.return_value = mock_current_user
        
        # Mock database queries for statistics
        mock_db = Mock()
        mock_accounts = [Mock(id=uuid4())]
        mock_db.query.return_value.filter.return_value.all.return_value = mock_accounts
        
        # Mock different count queries
        count_side_effects = [100, 80, 60, 20]  # total, categorized, auto, manual
        mock_db.query.return_value.filter.return_value.count.side_effect = count_side_effects
        
        # Mock confidence query
        confidence_results = [(0.8,), (0.9,), (0.7,)]
        mock_db.query.return_value.filter.return_value.all.return_value = confidence_results
        
        mock_get_db.return_value = mock_db
        
        response = client.get(
            '/api/categorization/stats',
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['total_transactions'] == 100
        assert data['categorized_transactions'] == 80
        assert data['categorization_rate'] == 80.0
        assert 'average_confidence' in data
    
    @patch('app.api.routers.categorization.get_current_user')
    @patch('app.api.routers.categorization.get_db')
    @patch('app.api.routers.categorization.ml_categorization_service')
    def test_auto_categorize_transaction(self, mock_ml_service, mock_get_db, mock_get_user,
                                       client, mock_current_user, auth_headers):
        """Test auto-categorizing a specific transaction"""
        mock_get_user.return_value = mock_current_user
        
        transaction_id = uuid4()
        
        # Mock transaction and account
        mock_transaction = Mock()
        mock_transaction.id = transaction_id
        mock_transaction.description = "WALMART SUPERCENTER"
        mock_transaction.amount = 45.67
        mock_transaction.transaction_type.value = "expense"
        mock_transaction.date = datetime(2024, 1, 15).date()
        mock_transaction.account_id = uuid4()
        
        mock_account = Mock()
        mock_account.id = mock_transaction.account_id
        mock_account.user_id = mock_current_user.id
        
        mock_category = Mock()
        mock_category.id = uuid4()
        mock_category.name = "Groceries"
        
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_transaction, mock_account, mock_category
        ]
        mock_get_db.return_value = mock_db
        
        # Mock ML prediction
        mock_ml_service.predict_category.return_value = {
            'predicted_category': 'Groceries',
            'confidence': 0.85,
            'needs_manual_review': False
        }
        
        response = client.post(
            f'/api/categorization/auto-categorize/{transaction_id}',
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'auto_categorized'
        assert data['category'] == 'Groceries'
        assert data['confidence'] == 0.85
    
    def test_predict_category_validation_error(self, client, auth_headers):
        """Test prediction with invalid request data"""
        request_data = {
            'description': '',  # Empty description
            'amount': 'invalid'  # Invalid amount type
        }
        
        response = client.post(
            '/api/categorization/predict',
            json=request_data,
            headers=auth_headers
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_bulk_predict_too_many_transactions(self, client, auth_headers):
        """Test bulk prediction with too many transactions"""
        request_data = {
            'transactions': [
                {
                    'description': f'Transaction {i}',
                    'amount': -50.0
                }
                for i in range(101)  # More than max allowed (100)
            ]
        }
        
        response = client.post(
            '/api/categorization/predict/bulk',
            json=request_data,
            headers=auth_headers
        )
        
        assert response.status_code == 422  # Validation error