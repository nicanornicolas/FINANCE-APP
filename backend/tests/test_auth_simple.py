import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from fastapi import HTTPException
import jwt

from app.main import app
from app.api.routers.auth import create_access_token, create_refresh_token
from app.core.config import settings


client = TestClient(app)


class TestTokenFunctions:
    """Test token creation and validation functions"""
    
    def test_create_access_token_default_expiry(self):
        """Test access token creation with default expiry"""
        data = {"sub": "test@example.com"}
        token = create_access_token(data)
        
        # Decode token to verify
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert payload["sub"] == "test@example.com"
        assert "exp" in payload
        
        # Check expiry is approximately 15 minutes from now (default)
        exp_time = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        expected_exp = datetime.now(timezone.utc) + timedelta(minutes=15)
        assert abs((exp_time - expected_exp).total_seconds()) < 60  # Within 1 minute
    
    def test_create_access_token_custom_expiry(self):
        """Test access token creation with custom expiry"""
        data = {"sub": "test@example.com"}
        expires_delta = timedelta(minutes=30)
        token = create_access_token(data, expires_delta)
        
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        exp_time = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        expected_exp = datetime.now(timezone.utc) + expires_delta
        assert abs((exp_time - expected_exp).total_seconds()) < 60  # Within 1 minute
    
    def test_create_refresh_token(self):
        """Test refresh token creation"""
        data = {"sub": "test@example.com"}
        token = create_refresh_token(data)
        
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert payload["sub"] == "test@example.com"
        assert "exp" in payload
        
        # Check expiry is approximately the configured days from now
        exp_time = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        expected_exp = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        assert abs((exp_time - expected_exp).total_seconds()) < 3600  # Within 1 hour
    
    def test_create_access_token_with_additional_claims(self):
        """Test access token creation with additional claims"""
        data = {"sub": "test@example.com", "role": "admin", "permissions": ["read", "write"]}
        token = create_access_token(data)
        
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert payload["sub"] == "test@example.com"
        assert payload["role"] == "admin"
        assert payload["permissions"] == ["read", "write"]
    
    def test_token_expiry_validation(self):
        """Test that expired tokens are properly identified"""
        # Create expired token
        expired_time = datetime.now(timezone.utc) - timedelta(minutes=30)
        data = {"sub": "test@example.com", "exp": expired_time.timestamp()}
        token = jwt.encode(data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        
        # Try to decode expired token
        with pytest.raises(jwt.ExpiredSignatureError):
            jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    
    def test_invalid_token_signature(self):
        """Test that tokens with invalid signatures are rejected"""
        data = {"sub": "test@example.com"}
        token = create_access_token(data)
        
        # Modify the token to make signature invalid
        invalid_token = token[:-5] + "XXXXX"
        
        with pytest.raises(jwt.InvalidSignatureError):
            jwt.decode(invalid_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    
    def test_token_with_wrong_algorithm(self):
        """Test that tokens created with wrong algorithm are rejected"""
        data = {"sub": "test@example.com"}
        # Create token with different algorithm
        wrong_token = jwt.encode(data, settings.SECRET_KEY, algorithm="HS512")

        with pytest.raises(jwt.InvalidAlgorithmError):
            jwt.decode(wrong_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])


class TestAuthEndpointsBasic:
    """Test basic authentication endpoints without database"""

    def test_logout_endpoint(self):
        """Test logout endpoint"""
        response = client.post("/auth/logout")
        assert response.status_code == 200
        assert "Successfully logged out" in response.json()["message"]

    def test_invalid_login_format(self):
        """Test login with invalid request format"""
        # Missing email field
        response = client.post("/auth/login", json={"password": "test123"})
        assert response.status_code == 422  # Validation error

        # Missing password field
        response = client.post("/auth/login", json={"email": "test@example.com"})
        assert response.status_code == 422  # Validation error

        # Empty request body
        response = client.post("/auth/login", json={})
        assert response.status_code == 422  # Validation error

    def test_invalid_register_format_validation_only(self):
        """Test registration validation without hitting database"""
        # Test that we can at least validate the request format
        # without hitting database issues

        # Invalid email format should fail validation before database
        from pydantic import ValidationError
        from app.schemas.user import UserCreate

        # Test invalid email
        try:
            UserCreate(
                email="invalid-email",
                password="test123",
                first_name="Test",
                last_name="User"
            )
            assert False, "Should have raised validation error"
        except ValidationError:
            pass  # Expected

        # Test missing fields
        try:
            UserCreate(email="test@example.com")  # Missing required fields
            assert False, "Should have raised validation error"
        except ValidationError:
            pass  # Expected

        # Test valid format
        user_data = UserCreate(
            email="test@example.com",
            password="validpassword",
            first_name="Test",
            last_name="User"
        )
        assert user_data.email == "test@example.com"
        assert user_data.first_name == "Test"


class TestPasswordValidation:
    """Test password validation and security"""

    def test_password_strength_validation_schema(self):
        """Test password validation at schema level"""
        from app.schemas.user import UserCreate
        from pydantic import ValidationError

        # Test various password scenarios
        test_cases = [
            {"password": "validpassword123", "should_pass": True},
            {"password": "Test123!", "should_pass": True},
            {"password": "verylongpasswordwithnospecialchars", "should_pass": True},
        ]

        for case in test_cases:
            try:
                user_data = UserCreate(
                    email=f"test_{len(case['password'])}@example.com",
                    password=case["password"],
                    first_name="Test",
                    last_name="User"
                )
                if case["should_pass"]:
                    assert user_data.password == case["password"]
                else:
                    assert False, f"Password '{case['password']}' should have failed validation"
            except ValidationError:
                if case["should_pass"]:
                    assert False, f"Password '{case['password']}' should have passed validation"
                # else: expected failure

    def test_password_hashing_function(self):
        """Test password hashing functionality"""
        from app.crud.user import CRUDUser
        from app.models.user import User

        crud_user = CRUDUser(User)

        password = "testpassword123"
        hashed = crud_user.get_password_hash(password)

        # Hash should be different from original
        assert hashed != password

        # Hash should start with bcrypt prefix
        assert hashed.startswith("$2b$")

        # Verify password should work
        assert crud_user.verify_password(password, hashed)

        # Wrong password should not verify
        assert not crud_user.verify_password("wrongpassword", hashed)


class TestJWTConfiguration:
    """Test JWT configuration and settings"""
    
    def test_jwt_settings_exist(self):
        """Test that JWT settings are properly configured"""
        assert hasattr(settings, 'SECRET_KEY')
        assert hasattr(settings, 'ALGORITHM')
        assert hasattr(settings, 'ACCESS_TOKEN_EXPIRE_MINUTES')
        assert hasattr(settings, 'REFRESH_TOKEN_EXPIRE_DAYS')
        
        assert settings.SECRET_KEY is not None
        assert settings.ALGORITHM == "HS256"
        assert settings.ACCESS_TOKEN_EXPIRE_MINUTES > 0
        assert settings.REFRESH_TOKEN_EXPIRE_DAYS > 0
    
    def test_secret_key_strength(self):
        """Test that secret key is sufficiently strong"""
        # Secret key should be at least 32 characters for security
        assert len(settings.SECRET_KEY) >= 32
        
        # Should not be a common weak key
        weak_keys = ["secret", "password", "123456", "your-secret-key"]
        assert settings.SECRET_KEY not in weak_keys
