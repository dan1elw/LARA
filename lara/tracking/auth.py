"""
OpenSky Network OAuth2 Authentication
Handles OAuth2 Client Credentials Flow for OpenSky API using Keycloak.
"""

import requests
import json
import time
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timedelta


class OpenSkyAuth:
    """
    Manages OAuth2 authentication for OpenSky Network API.
    
    Uses OAuth2 Client Credentials Flow via Keycloak (OpenID Connect).
    """
    
    # Correct Keycloak OAuth2 endpoint
    TOKEN_URL = "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token"
    
    def __init__(self, credentials_path: Optional[str] = None,
                 client_id: Optional[str] = None,
                 client_secret: Optional[str] = None):
        """
        Initialize OpenSky OAuth2 authentication.
        
        Args:
            credentials_path: Path to credentials.json file from OpenSky
            client_id: OAuth2 client ID (alternative to credentials file)
            client_secret: OAuth2 client secret (alternative to credentials file)
        
        Either provide credentials_path OR both client_id and client_secret.
        """
        self.client_id = None
        self.client_secret = None
        self.access_token = None
        self.token_expires_at = None
        self.token_type = "Bearer"
        
        # Load credentials
        if credentials_path:
            self._load_credentials_from_file(credentials_path)
        elif client_id and client_secret:
            self.client_id = client_id
            self.client_secret = client_secret
        else:
            raise ValueError(
                "Either credentials_path or both client_id and client_secret must be provided"
            )
    
    def _load_credentials_from_file(self, credentials_path: str):
        """
        Load OAuth2 credentials from JSON file.
        
        Expected format:
        {
            "clientId": "your-client-id",
            "clientSecret": "your-client-secret"
        }
        
        Args:
            credentials_path: Path to credentials.json
        """
        try:
            with open(credentials_path, 'r') as f:
                creds = json.load(f)
            
            self.client_id = creds.get('clientId')
            self.client_secret = creds.get('clientSecret')
            
            if not self.client_id or not self.client_secret:
                raise ValueError(
                    "credentials.json must contain 'clientId' and 'clientSecret'"
                )
            
            print(f"✅ Loaded OAuth2 credentials from {credentials_path}")
            print(f"   Client ID: {self.client_id}")
            
        except FileNotFoundError:
            raise FileNotFoundError(
                f"Credentials file not found: {credentials_path}\n"
                f"Download it from OpenSky Network -> My Account -> API Client"
            )
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in credentials file: {e}")
    
    def _request_token(self) -> Dict[str, Any]:
        """
        Request new access token from OpenSky Keycloak server.
        
        Returns:
            Token response dictionary
        
        Raises:
            Exception: If token request fails
        """
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        data = {
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }
        
        try:
            response = requests.post(
                self.TOKEN_URL,
                headers=headers,
                data=data,
                timeout=10
            )
            
            # Check for errors
            if response.status_code != 200:
                error_msg = f"Token request failed with status {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg += f"\nError: {error_data.get('error', 'unknown')}"
                    error_msg += f"\nDescription: {error_data.get('error_description', 'no description')}"
                except:
                    error_msg += f"\nResponse: {response.text[:200]}"
                
                raise Exception(error_msg)
            
            token_data = response.json()
            return token_data
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to obtain access token: {e}")
    
    def get_token(self, force_refresh: bool = False) -> str:
        """
        Get valid access token, refreshing if necessary.
        
        Args:
            force_refresh: Force token refresh even if current token is valid
        
        Returns:
            Valid access token
        
        Raises:
            Exception: If unable to obtain token
        """
        # Check if we need a new token
        if force_refresh or not self._is_token_valid():
            print("🔄 Requesting new OAuth2 access token...")
            
            token_data = self._request_token()
            
            self.access_token = token_data.get('access_token')
            self.token_type = token_data.get('token_type', 'Bearer')
            expires_in = token_data.get('expires_in', 1800)  # Default 30 minutes
            
            # Set expiration time (with 2 minute buffer)
            self.token_expires_at = datetime.now() + timedelta(seconds=expires_in - 120)
            
            print(f"✅ Access token obtained (expires in {expires_in}s)")
        
        return self.access_token
    
    def _is_token_valid(self) -> bool:
        """
        Check if current token is still valid.
        
        Returns:
            True if token exists and hasn't expired
        """
        if not self.access_token or not self.token_expires_at:
            return False
        
        return datetime.now() < self.token_expires_at
    
    def get_auth_headers(self) -> Dict[str, str]:
        """
        Get authentication headers for API requests.
        
        Returns:
            Dictionary with Authorization header
        
        Example:
            {'Authorization': 'Bearer eyJhbGciOiJIUzI1NiIs...'}
        """
        token = self.get_token()
        return {
            'Authorization': f'{self.token_type} {token}'
        }
    
    def make_authenticated_request(self, url: str, params: Optional[Dict] = None,
                                   timeout: int = 10) -> requests.Response:
        """
        Make authenticated request to OpenSky API.
        
        Args:
            url: API endpoint URL
            params: Query parameters
            timeout: Request timeout in seconds
        
        Returns:
            Response object
        
        Raises:
            requests.exceptions.RequestException: If request fails
        """
        headers = self.get_auth_headers()
        
        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=timeout
        )
        
        # Handle token expiration during request
        if response.status_code == 401:
            # Token might have expired, try refreshing
            print("⚠️  Token expired during request, refreshing...")
            self.access_token = None  # Force refresh
            headers = self.get_auth_headers()
            
            response = requests.get(
                url,
                headers=headers,
                params=params,
                timeout=timeout
            )
        
        return response
    
    def test_authentication(self) -> bool:
        """
        Test if authentication is working.
        
        Returns:
            True if authentication successful, False otherwise
        """
        try:
            print("🧪 Testing OAuth2 authentication...")
            
            # Try to get a token
            token = self.get_token()
            
            if not token:
                print("❌ Failed to obtain token")
                return False
            
            # Test with a simple API call
            print("   Making test API request...")
            headers = self.get_auth_headers()
            response = requests.get(
                "https://opensky-network.org/api/states/all",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                print("✅ Authentication test successful!")
                print("   API responded with valid data")
                return True
            elif response.status_code == 401:
                print(f"❌ Authentication test failed: Token not accepted (401)")
                print(f"   The token was issued but API rejected it")
                return False
            else:
                print(f"❌ Authentication test failed: HTTP {response.status_code}")
                if response.text:
                    print(f"   Response: {response.text[:200]}")
                return False
                
        except Exception as e:
            print(f"❌ Authentication test failed: {e}")
            return False
    
    def invalidate_token(self):
        """Invalidate current token (forces refresh on next request)."""
        self.access_token = None
        self.token_expires_at = None


# ============================================================================
# Fallback: Basic Authentication (deprecated but still works)
# ============================================================================

class OpenSkyBasicAuth:
    """
    Basic authentication for OpenSky (deprecated but still functional).
    Use this as fallback if OAuth2 doesn't work yet.
    """
    
    def __init__(self, username: str, password: str):
        """
        Initialize basic authentication.
        
        Args:
            username: OpenSky username
            password: OpenSky password
        """
        self.username = username
        self.password = password
        self.credentials = (username, password)
        self.client_id = username  # For display purposes
    
    def make_authenticated_request(self, url: str, params: Optional[Dict] = None,
                                   timeout: int = 10) -> requests.Response:
        """Make authenticated request using basic auth."""
        response = requests.get(
            url,
            auth=self.credentials,
            params=params,
            timeout=timeout
        )
        return response
    
    def test_authentication(self) -> bool:
        """Test if basic authentication is working."""
        try:
            print("🧪 Testing basic authentication...")
            
            response = requests.get(
                "https://opensky-network.org/api/states/all",
                auth=self.credentials,
                timeout=10
            )
            
            if response.status_code == 200:
                print("✅ Basic authentication successful!")
                print("   ⚠️  Note: Basic auth is deprecated, consider OAuth2")
                return True
            else:
                print(f"❌ Basic authentication failed: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Basic authentication test failed: {e}")
            return False


# ============================================================================
# Helper function for easy authentication
# ============================================================================

def create_auth_from_config(config) -> Optional[Any]:
    """
    Create authentication instance from LARA configuration.
    
    Args:
        config: LARA Config object
    
    Returns:
        Auth instance (OAuth2 or Basic) if credentials configured, None otherwise
    """
    # Try OAuth2 first (recommended)
    credentials_path = config.get('api.credentials_path')
    
    if credentials_path:
        try:
            auth = OpenSkyAuth(credentials_path=credentials_path)
            # Test it
            if auth.test_authentication():
                return auth
            else:
                print("⚠️  OAuth2 authentication test failed")
                print("   Falling back to anonymous mode")
                return None
        except Exception as e:
            print(f"⚠️  OAuth2 initialization failed: {e}")
            print(f"   Falling back to anonymous mode")
    
    # Try direct OAuth2 credentials
    client_id = config.get('api.client_id')
    client_secret = config.get('api.client_secret')
    
    if client_id and client_secret:
        try:
            auth = OpenSkyAuth(client_id=client_id, client_secret=client_secret)
            if auth.test_authentication():
                return auth
            else:
                print("⚠️  OAuth2 authentication test failed")
                return None
        except Exception as e:
            print(f"⚠️  OAuth2 initialization failed: {e}")
    
    # Try basic auth as fallback (deprecated but might still work)
    username = config.get('api.username')
    password = config.get('api.password')
    
    if username and password:
        try:
            print("ℹ️  Trying basic authentication (deprecated)...")
            auth = OpenSkyBasicAuth(username, password)
            if auth.test_authentication():
                return auth
            else:
                print("⚠️  Basic authentication failed")
                return None
        except Exception as e:
            print(f"⚠️  Basic auth failed: {e}")
    
    # No authentication configured or all methods failed
    return None


# ============================================================================
# Example usage and testing
# ============================================================================

if __name__ == "__main__":
    """
    Test OAuth2 authentication with your credentials.
    
    Usage:
        python -m lara.tracking.auth [path/to/credentials.json]
    """
    import sys
    
    print("=" * 70)
    print("OpenSky Network OAuth2 Authentication Test")
    print("=" * 70)
    
    # Check if credentials file provided as argument
    if len(sys.argv) > 1:
        credentials_path = sys.argv[1]
    else:
        credentials_path = "credentials.json"
    
    try:
        # Initialize authentication
        auth = OpenSkyAuth(credentials_path=credentials_path)
        
        # Test authentication
        if auth.test_authentication():
            print("\n✅ Your OAuth2 credentials are working correctly!")
            print(f"   Client ID: {auth.client_id}")
            print(f"   Token valid until: {auth.token_expires_at}")
            print("\n   You can now use authenticated API access!")
        else:
            print("\n❌ Authentication test failed")
            print("   Check your credentials and try again")
            print("\n   For now, you can use anonymous mode")
            sys.exit(1)
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nUsage:")
        print("  python -m lara.tracking.auth [path/to/credentials.json]")
        print("\nOr use anonymous mode by not configuring credentials")
        sys.exit(1)
