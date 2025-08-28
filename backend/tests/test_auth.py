import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from fastapi import HTTPException
from sqlalchemy.orm import Session
import jwt

from app.main import app
from app.api.routers.auth import create_access_token, create_refresh_token, get_current_user
from app.crud import user as crud_user
from app.schemas.user import UserCreate, UserLogin
from app.core.config import settings
from app.models.user import User as UserModel


client = TestClient(app)


class TestAuthEndpoints:
    """Test authentication endpoints"""
    
    def test_register_success(self, db_session):
        """Test successful user registration"""
        user_data = {
            "email": "test@example.com",
            "password": "testpassword123",
            "first_name": "Test",
            "last_name": "User"
        }
        
        response = client.post("/auth/register", json=user_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == user_data["email"]
        assert data["user"]["first_name"] == user_data["first_name"]
        assert data["user"]["last_name"] == user_data["last_name"]
    
    def test_register_duplicate_email(self, db_session):
        """Test registration with duplicate email"""
        user_data = {
            "email": "duplicate@example.com",
            "password": "testpassword123",
            "first_name": "Test",
            "last_name": "User"
        }
        
        # First registration
        response1 = client.post("/auth/register", json=user_data)
        assert response1.status_code == 200
        
        # Second registration with same email
        response2 = client.post("/auth/register", json=user_data)
        assert response2.status_code == 400
        assert "Email already registered" in response2.json()["detail"]
    
    def test_register_invalid_email(self, db_session):
        """Test registration with invalid email"""
        user_data = {
            "email": "invalid-email",
            "password": "testpassword123",
            "first_name": "Test",
            "last_name": "User"
        }
        
        response = client.post("/auth/register", json=user_data)
        assert response.status_code == 422  # Validation error
    
    def test_register_missing_fields(self, db_session):
        """Test registration with missing required fields"""
        user_data = {
            "email": "test@example.com",
            # Missing password, first_name, last_name
        }
        
        response = client.post("/auth/register", json=user_data)
        assert response.status_code == 422  # Validation error
    
    def test_login_success(self, db_session):
        """Test successful login"""
        # Create user first
        user_create = UserCreate(
            email="login@example.com",
            password="testpassword123",
            first_name="Login",
            last_name="User"
        )
        crud_user.user.create(db_session, obj_in=user_create)
        
        login_data = {
            "email": "login@example.com",
            "password": "testpassword123"
        }
        
        response = client.post("/auth/login", json=login_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == login_data["email"]
    
    def test_login_wrong_password(self, db_session):
        """Test login with wrong password"""
        # Create user first
        user_create = UserCreate(
            email="wrongpass@example.com",
            password="correctpassword",
            first_name="Wrong",
            last_name="Pass"
        )
        crud_user.user.create(db_session, obj_in=user_create)
        
        login_data = {
            "email": "wrongpass@example.com",
            "password": "wrongpassword"
        }
        
        response = client.post("/auth/login", json=login_data)
        
        assert response.status_code == 401
        assert "Incorrect email or password" in response.json()["detail"]
    
    def test_login_nonexistent_user(self, db_session):
        """Test login with non-existent user"""
        login_data = {
            "email": "nonexistent@example.com",
            "password": "somepassword"
        }
        
        response = client.post("/auth/login", json=login_data)
        
        assert response.status_code == 401
        assert "Incorrect email or password" in response.json()["detail"]
    
    def test_login_invalid_email_format(self, db_session):
        """Test login with invalid email format"""
        login_data = {
            "email": "invalid-email",
            "password": "somepassword"
        }
        
        response = client.post("/auth/login", json=login_data)
        assert response.status_code == 422  # Validation error


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


class TestGetCurrentUser:
    """Test get_current_user dependency function"""

    @pytest.mark.asyncio
    async def test_get_current_user_valid_token(self, db_session):
        """Test getting current user with valid token"""
        # Create user
        user_create = UserCreate(
            email="currentuser@example.com",
            password="testpassword123",
            first_name="Current",
            last_name="User"
        )
        user = crud_user.user.create(db_session, obj_in=user_create)

        # Create token
        token = create_access_token({"sub": user.email})

        # Mock credentials
        from fastapi.security import HTTPAuthorizationCredentials
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        # Test function
        current_user = await get_current_user(credentials, db_session)
        assert current_user.email == user.email
        assert current_user.id == user.id

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self, db_session):
        """Test getting current user with invalid token"""
        from fastapi.security import HTTPAuthorizationCredentials
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid_token")

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials, db_session)

        assert exc_info.value.status_code == 401
        assert "Could not validate credentials" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_current_user_expired_token(self, db_session):
        """Test getting current user with expired token"""
        # Create expired token
        expired_time = datetime.now(timezone.utc) - timedelta(minutes=30)
        data = {"sub": "test@example.com", "exp": expired_time.timestamp()}
        token = jwt.encode(data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

        from fastapi.security import HTTPAuthorizationCredentials
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials, db_session)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_user_nonexistent_user(self, db_session):
        """Test getting current user with token for non-existent user"""
        # Create token for non-existent user
        token = create_access_token({"sub": "nonexistent@example.com"})

        from fastapi.security import HTTPAuthorizationCredentials
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials, db_session)

        assert exc_info.value.status_code == 401
        assert "Could not validate credentials" in str(exc_info.value.detail)


class TestProtectedEndpoints:
    """Test protected endpoints that require authentication"""

    def test_get_profile_success(self, db_session):
        """Test getting user profile with valid token"""
        # Create user
        user_create = UserCreate(
            email="profile@example.com",
            password="testpassword123",
            first_name="Profile",
            last_name="User"
        )
        user = crud_user.user.create(db_session, obj_in=user_create)

        # Create token
        token = create_access_token({"sub": user.email})

        # Make request with token
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/auth/profile", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == user.email
        assert data["first_name"] == user.first_name
        assert data["last_name"] == user.last_name

    def test_get_profile_no_token(self, db_session):
        """Test getting user profile without token"""
        response = client.get("/auth/profile")
        assert response.status_code == 403  # Forbidden

    def test_get_profile_invalid_token(self, db_session):
        """Test getting user profile with invalid token"""
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.get("/auth/profile", headers=headers)
        assert response.status_code == 401

    def test_logout_success(self, db_session):
        """Test logout endpoint"""
        response = client.post("/auth/logout")
        assert response.status_code == 200
        assert "Successfully logged out" in response.json()["message"]


class TestPasswordSecurity:
    """Test password security features"""

    def test_password_hashing(self, db_session):
        """Test that passwords are properly hashed"""
        user_create = UserCreate(
            email="hash@example.com",
            password="plainpassword123",
            first_name="Hash",
            last_name="User"
        )
        user = crud_user.user.create(db_session, obj_in=user_create)

        # Password should be hashed, not stored in plain text
        assert user.password_hash != "plainpassword123"
        assert user.password_hash.startswith("$2b$")  # bcrypt hash format

    def test_password_verification(self, db_session):
        """Test password verification"""
        user_create = UserCreate(
            email="verify@example.com",
            password="testpassword123",
            first_name="Verify",
            last_name="User"
        )
        user = crud_user.user.create(db_session, obj_in=user_create)

        # Test correct password
        authenticated_user = crud_user.user.authenticate(
            db_session, email=user.email, password="testpassword123"
        )
        assert authenticated_user is not None
        assert authenticated_user.id == user.id

        # Test wrong password
        wrong_auth = crud_user.user.authenticate(
            db_session, email=user.email, password="wrongpassword"
        )
        assert wrong_auth is None
