"""
Multi-Factor Authentication service.
"""
import secrets
import qrcode
import io
import base64
import json
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
import pyotp
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import logging

from ..models.mfa import MFAMethod, MFAAttempt, MFASession
from ..models.user import User
from ..core.security import encryption_manager, security_utils
from ..core.config import settings


logger = logging.getLogger(__name__)


class MFAService:
    """Service for managing Multi-Factor Authentication."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def setup_totp(self, user_id: str, method_name: str = "Authenticator App") -> Dict[str, Any]:
        """
        Set up TOTP (Time-based One-Time Password) for a user.
        
        Args:
            user_id: User ID
            method_name: User-friendly name for the method
        
        Returns:
            Dictionary containing secret key, QR code, and backup codes
        """
        try:
            # Generate secret key
            secret = pyotp.random_base32()
            
            # Get user details
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                raise ValueError("User not found")
            
            # Create TOTP URI for QR code
            totp = pyotp.TOTP(secret)
            provisioning_uri = totp.provisioning_uri(
                name=user.email,
                issuer_name="Finance App"
            )
            
            # Generate QR code
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(provisioning_uri)
            qr.make(fit=True)
            
            qr_image = qr.make_image(fill_color="black", back_color="white")
            qr_buffer = io.BytesIO()
            qr_image.save(qr_buffer, format='PNG')
            qr_code_base64 = base64.b64encode(qr_buffer.getvalue()).decode()
            
            # Generate backup codes
            backup_codes = [secrets.token_hex(4).upper() for _ in range(10)]
            
            # Encrypt sensitive data
            encrypted_secret = encryption_manager.encrypt(secret)
            encrypted_backup_codes = encryption_manager.encrypt(json.dumps(backup_codes))
            
            # Create MFA method (not verified yet)
            mfa_method = MFAMethod(
                user_id=user_id,
                method_type="totp",
                method_name=method_name,
                secret_key=encrypted_secret,
                backup_codes=encrypted_backup_codes,
                is_active=True,
                is_verified=False
            )
            
            self.db.add(mfa_method)
            self.db.commit()
            self.db.refresh(mfa_method)
            
            return {
                "method_id": str(mfa_method.id),
                "secret": secret,  # Only return for initial setup
                "qr_code": f"data:image/png;base64,{qr_code_base64}",
                "backup_codes": backup_codes,
                "provisioning_uri": provisioning_uri
            }
            
        except SQLAlchemyError as e:
            logger.error(f"Database error setting up TOTP: {e}")
            self.db.rollback()
            raise
        except Exception as e:
            logger.error(f"Error setting up TOTP: {e}")
            raise
    
    def verify_totp_setup(self, method_id: str, code: str) -> bool:
        """
        Verify TOTP setup by validating the provided code.
        
        Args:
            method_id: MFA method ID
            code: TOTP code provided by user
        
        Returns:
            True if verification successful, False otherwise
        """
        try:
            mfa_method = self.db.query(MFAMethod).filter(
                MFAMethod.id == method_id,
                MFAMethod.method_type == "totp",
                MFAMethod.is_active == True
            ).first()
            
            if not mfa_method:
                return False
            
            # Decrypt secret
            secret = encryption_manager.decrypt(mfa_method.secret_key)
            if not secret:
                return False
            
            # Verify code
            totp = pyotp.TOTP(secret)
            is_valid = totp.verify(code, valid_window=1)  # Allow 1 window tolerance
            
            if is_valid:
                # Mark as verified
                mfa_method.is_verified = True
                self.db.commit()
                
                # Log successful setup
                self._log_mfa_attempt(
                    mfa_method.user_id,
                    method_id,
                    "totp",
                    True,
                    code
                )
            else:
                # Log failed attempt
                self._log_mfa_attempt(
                    mfa_method.user_id,
                    method_id,
                    "totp",
                    False,
                    code
                )
            
            return is_valid
            
        except Exception as e:
            logger.error(f"Error verifying TOTP setup: {e}")
            return False
    
    def verify_totp(self, user_id: str, code: str) -> bool:
        """
        Verify TOTP code for authentication.
        
        Args:
            user_id: User ID
            code: TOTP code provided by user
        
        Returns:
            True if verification successful, False otherwise
        """
        try:
            # Get active TOTP method
            mfa_method = self.db.query(MFAMethod).filter(
                MFAMethod.user_id == user_id,
                MFAMethod.method_type == "totp",
                MFAMethod.is_active == True,
                MFAMethod.is_verified == True
            ).first()
            
            if not mfa_method:
                return False
            
            # Decrypt secret
            secret = encryption_manager.decrypt(mfa_method.secret_key)
            if not secret:
                return False
            
            # Verify code
            totp = pyotp.TOTP(secret)
            is_valid = totp.verify(code, valid_window=1)
            
            if is_valid:
                # Update usage tracking
                mfa_method.last_used = datetime.utcnow()
                mfa_method.use_count += 1
                self.db.commit()
            
            # Log attempt
            self._log_mfa_attempt(
                user_id,
                str(mfa_method.id),
                "totp",
                is_valid,
                code
            )
            
            return is_valid
            
        except Exception as e:
            logger.error(f"Error verifying TOTP: {e}")
            return False
    
    def verify_backup_code(self, user_id: str, code: str) -> bool:
        """
        Verify backup code for authentication.
        
        Args:
            user_id: User ID
            code: Backup code provided by user
        
        Returns:
            True if verification successful, False otherwise
        """
        try:
            # Get TOTP method with backup codes
            mfa_method = self.db.query(MFAMethod).filter(
                MFAMethod.user_id == user_id,
                MFAMethod.method_type == "totp",
                MFAMethod.is_active == True,
                MFAMethod.is_verified == True,
                MFAMethod.backup_codes.isnot(None)
            ).first()
            
            if not mfa_method:
                return False
            
            # Decrypt backup codes
            encrypted_codes = mfa_method.backup_codes
            backup_codes_json = encryption_manager.decrypt(encrypted_codes)
            if not backup_codes_json:
                return False
            
            backup_codes = json.loads(backup_codes_json)
            
            # Check if code is valid and not used
            code_upper = code.upper().strip()
            if code_upper in backup_codes:
                # Remove used code
                backup_codes.remove(code_upper)
                
                # Update backup codes
                updated_codes = encryption_manager.encrypt(json.dumps(backup_codes))
                mfa_method.backup_codes = updated_codes
                mfa_method.last_used = datetime.utcnow()
                mfa_method.use_count += 1
                self.db.commit()
                
                # Log successful attempt
                self._log_mfa_attempt(
                    user_id,
                    str(mfa_method.id),
                    "backup_code",
                    True,
                    code
                )
                
                return True
            
            # Log failed attempt
            self._log_mfa_attempt(
                user_id,
                str(mfa_method.id),
                "backup_code",
                False,
                code
            )
            
            return False
            
        except Exception as e:
            logger.error(f"Error verifying backup code: {e}")
            return False
    
    def get_user_mfa_methods(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all MFA methods for a user.
        
        Args:
            user_id: User ID
        
        Returns:
            List of MFA method information
        """
        try:
            methods = self.db.query(MFAMethod).filter(
                MFAMethod.user_id == user_id,
                MFAMethod.is_active == True
            ).all()
            
            result = []
            for method in methods:
                method_info = {
                    "id": str(method.id),
                    "method_type": method.method_type,
                    "method_name": method.method_name,
                    "is_verified": method.is_verified,
                    "last_used": method.last_used.isoformat() if method.last_used else None,
                    "use_count": method.use_count,
                    "created_at": method.created_at.isoformat()
                }
                
                # Add method-specific info
                if method.method_type == "totp" and method.backup_codes:
                    # Count remaining backup codes
                    try:
                        backup_codes_json = encryption_manager.decrypt(method.backup_codes)
                        backup_codes = json.loads(backup_codes_json) if backup_codes_json else []
                        method_info["backup_codes_remaining"] = len(backup_codes)
                    except:
                        method_info["backup_codes_remaining"] = 0
                
                result.append(method_info)
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting user MFA methods: {e}")
            return []
    
    def disable_mfa_method(self, method_id: str, user_id: str) -> bool:
        """
        Disable an MFA method.
        
        Args:
            method_id: MFA method ID
            user_id: User ID (for security)
        
        Returns:
            True if successful, False otherwise
        """
        try:
            mfa_method = self.db.query(MFAMethod).filter(
                MFAMethod.id == method_id,
                MFAMethod.user_id == user_id
            ).first()
            
            if not mfa_method:
                return False
            
            mfa_method.is_active = False
            self.db.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Error disabling MFA method: {e}")
            self.db.rollback()
            return False
    
    def create_mfa_session(
        self, 
        user_id: str, 
        challenge_type: str = "login",
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Optional[str]:
        """
        Create a temporary MFA session for multi-step authentication.
        
        Args:
            user_id: User ID
            challenge_type: Type of challenge ("login", "sensitive_operation")
            ip_address: Client IP address
            user_agent: Client user agent
        
        Returns:
            Session token if successful, None otherwise
        """
        try:
            # Generate session token
            session_token = security_utils.generate_secure_token(32)
            
            # Set expiry (5 minutes for MFA sessions)
            expires_at = datetime.utcnow() + timedelta(minutes=5)
            
            mfa_session = MFASession(
                user_id=user_id,
                session_token=session_token,
                challenge_type=challenge_type,
                expires_at=expires_at,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            self.db.add(mfa_session)
            self.db.commit()
            
            return session_token
            
        except Exception as e:
            logger.error(f"Error creating MFA session: {e}")
            self.db.rollback()
            return None
    
    def verify_mfa_session(self, session_token: str) -> Optional[MFASession]:
        """
        Verify and retrieve MFA session.
        
        Args:
            session_token: Session token
        
        Returns:
            MFASession if valid, None otherwise
        """
        try:
            session = self.db.query(MFASession).filter(
                MFASession.session_token == session_token
            ).first()
            
            if session and session.is_valid:
                return session
            
            return None
            
        except Exception as e:
            logger.error(f"Error verifying MFA session: {e}")
            return None
    
    def complete_mfa_session(self, session_token: str) -> bool:
        """
        Mark MFA session as completed.
        
        Args:
            session_token: Session token
        
        Returns:
            True if successful, False otherwise
        """
        try:
            session = self.db.query(MFASession).filter(
                MFASession.session_token == session_token
            ).first()
            
            if session and session.is_valid:
                session.mark_verified()
                self.db.commit()
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error completing MFA session: {e}")
            self.db.rollback()
            return False
    
    def user_has_mfa(self, user_id: str) -> bool:
        """
        Check if user has any active MFA methods.
        
        Args:
            user_id: User ID
        
        Returns:
            True if user has active MFA, False otherwise
        """
        try:
            count = self.db.query(MFAMethod).filter(
                MFAMethod.user_id == user_id,
                MFAMethod.is_active == True,
                MFAMethod.is_verified == True
            ).count()
            
            return count > 0
            
        except Exception as e:
            logger.error(f"Error checking user MFA status: {e}")
            return False
    
    def _log_mfa_attempt(
        self,
        user_id: str,
        method_id: Optional[str],
        method_type: str,
        success: bool,
        code: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """Log MFA attempt for security monitoring."""
        try:
            # Hash the code for security (don't store plaintext)
            code_hash = security_utils.hash_with_salt(code, "mfa_attempt")
            
            attempt = MFAAttempt(
                user_id=user_id,
                mfa_method_id=method_id,
                method_type=method_type,
                code_provided=code_hash,
                success=success,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            self.db.add(attempt)
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Error logging MFA attempt: {e}")
            # Don't raise exception as this is just logging