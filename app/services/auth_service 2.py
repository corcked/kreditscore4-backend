import secrets
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

class AuthTokenService:
    """Service for managing temporary auth tokens"""
    
    def __init__(self):
        self.auth_tokens: Dict[str, dict] = {}
        self.loan_data_storage: Dict[str, dict] = {}
        self.token_user_mapping: Dict[str, int] = {}
    
    def create_auth_token(self, loan_data: Optional[dict] = None) -> str:
        """Create a new auth token with optional loan data"""
        auth_token = secrets.token_urlsafe(32)
        
        self.auth_tokens[auth_token] = {
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(minutes=10)
        }
        
        if loan_data:
            self.loan_data_storage[auth_token] = loan_data
        
        return auth_token
    
    def verify_auth_token(self, auth_token: str) -> Tuple[bool, Optional[str]]:
        """Verify if auth token is valid and not expired"""
        auth_data = self.auth_tokens.get(auth_token)
        
        if not auth_data:
            return False, "Invalid or expired auth token"
        
        if auth_data["expires_at"] < datetime.utcnow():
            self.cleanup_auth_token(auth_token)
            return False, "Auth token expired"
        
        return True, None
    
    def get_loan_data(self, auth_token: str) -> Optional[dict]:
        """Get loan data associated with auth token"""
        return self.loan_data_storage.get(auth_token)
    
    def set_user_for_token(self, auth_token: str, user_id: int):
        """Associate user ID with auth token"""
        self.token_user_mapping[auth_token] = user_id
    
    def get_user_by_token(self, auth_token: str) -> Optional[int]:
        """Get user ID by auth token"""
        return self.token_user_mapping.get(auth_token)
    
    def cleanup_auth_token(self, auth_token: str):
        """Remove auth token and associated data"""
        if auth_token in self.auth_tokens:
            del self.auth_tokens[auth_token]
        if auth_token in self.loan_data_storage:
            del self.loan_data_storage[auth_token]
        if auth_token in self.token_user_mapping:
            del self.token_user_mapping[auth_token]
    
    def cleanup_expired_tokens(self):
        """Remove all expired tokens"""
        current_time = datetime.utcnow()
        expired_tokens = [
            token for token, data in self.auth_tokens.items()
            if data["expires_at"] < current_time
        ]
        
        for token in expired_tokens:
            self.cleanup_auth_token(token)


# Singleton instance
auth_token_service = AuthTokenService()