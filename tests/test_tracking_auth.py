"""
Tests for LARA OpenSky Network OAuth2 Authentication.

This test suite covers:
- OpenSkyAuth class initialization and configuration
- Token request and refresh mechanisms
- Authentication header generation
- Request handling with automatic token refresh
- Error handling for various failure scenarios
- OpenSkyBasicAuth fallback authentication
- Helper function for creating auth from config
"""

import pytest
import json
import tempfile
import os
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from typing import Dict, Any

# Assuming the auth module is importable - adjust path as needed
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from lara.tracking.auth import OpenSkyAuth, OpenSkyBasicAuth, create_auth_from_config

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def valid_credentials() -> Dict[str, str]:
    """Valid OAuth2 credentials for testing."""
    return {"clientId": "test-client-id", "clientSecret": "test-client-secret"}


@pytest.fixture
def credentials_file(valid_credentials: Dict[str, str]) -> str:
    """Create temporary credentials.json file."""
    fd, path = tempfile.mkstemp(suffix=".json")

    with os.fdopen(fd, "w") as f:
        json.dump(valid_credentials, f)

    yield path

    # Cleanup
    try:
        os.unlink(path)
    except:
        pass


@pytest.fixture
def invalid_credentials_file() -> str:
    """Create credentials file with invalid format."""
    fd, path = tempfile.mkstemp(suffix=".json")

    with os.fdopen(fd, "w") as f:
        json.dump({"invalid": "format"}, f)

    yield path

    try:
        os.unlink(path)
    except:
        pass


@pytest.fixture
def mock_token_response() -> Dict[str, Any]:
    """Mock successful token response from Keycloak."""
    return {
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test",
        "token_type": "Bearer",
        "expires_in": 1800,  # 30 minutes
        "refresh_expires_in": 3600,
        "scope": "openid",
    }


@pytest.fixture
def mock_config():
    """Mock LARA configuration object."""
    config = Mock()
    config.get = Mock(
        side_effect=lambda key, default=None: {
            "api.credentials_path": "credentials.json",
            "api.client_id": None,
            "api.client_secret": None,
            "api.username": None,
            "api.password": None,
        }.get(key, default)
    )
    return config


# ============================================================================
# OpenSkyAuth Tests - Initialization
# ============================================================================


class TestOpenSkyAuthInitialization:
    """Tests for OpenSkyAuth initialization and credential loading."""

    def test_init_with_credentials_file(self, credentials_file: str, capsys):
        """Test initialization with valid credentials file."""
        auth = OpenSkyAuth(credentials_path=credentials_file)

        assert auth.client_id == "test-client-id"
        assert auth.client_secret == "test-client-secret"
        assert auth.access_token is None
        assert auth.token_expires_at is None
        assert auth.token_type == "Bearer"

        # Check console output
        captured = capsys.readouterr()
        assert "OAuth2 credentials" in captured.out
        assert "test-client-id" in captured.out

    def test_init_with_direct_credentials(self):
        """Test initialization with direct client_id and client_secret."""
        auth = OpenSkyAuth(
            client_id="direct-client-id", client_secret="direct-client-secret"
        )

        assert auth.client_id == "direct-client-id"
        assert auth.client_secret == "direct-client-secret"

    def test_init_missing_credentials_raises_error(self):
        """Test that initialization without credentials raises ValueError."""
        with pytest.raises(
            ValueError, match="Either credentials_path or both client_id"
        ):
            OpenSkyAuth()

    def test_init_partial_credentials_raises_error(self):
        """Test that providing only client_id or client_secret raises error."""
        with pytest.raises(
            ValueError, match="Either credentials_path or both client_id"
        ):
            OpenSkyAuth(client_id="only-id")

        with pytest.raises(
            ValueError, match="Either credentials_path or both client_id"
        ):
            OpenSkyAuth(client_secret="only-secret")

    def test_load_credentials_file_not_found(self):
        """Test handling of missing credentials file."""
        with pytest.raises(FileNotFoundError, match="Credentials file not found"):
            OpenSkyAuth(credentials_path="/nonexistent/credentials.json")

    def test_load_credentials_invalid_json(self):
        """Test handling of invalid JSON in credentials file."""
        fd, path = tempfile.mkstemp(suffix=".json")

        try:
            with os.fdopen(fd, "w") as f:
                f.write("{ invalid json }")

            with pytest.raises(ValueError, match="Invalid JSON"):
                OpenSkyAuth(credentials_path=path)
        finally:
            os.unlink(path)

    def test_load_credentials_missing_fields(self, invalid_credentials_file: str):
        """Test handling of credentials file with missing required fields."""
        with pytest.raises(
            ValueError, match="must contain 'clientId' and 'clientSecret'"
        ):
            OpenSkyAuth(credentials_path=invalid_credentials_file)


# ============================================================================
# OpenSkyAuth Tests - Token Management
# ============================================================================


class TestOpenSkyAuthTokenManagement:
    """Tests for token request, validation, and refresh."""

    @patch("lara.tracking.auth.requests.post")
    def test_request_token_success(
        self,
        mock_post: Mock,
        mock_token_response: Dict[str, Any],
        credentials_file: str,
    ):
        """Test successful token request."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_token_response
        mock_post.return_value = mock_response

        auth = OpenSkyAuth(credentials_path=credentials_file)
        token_data = auth._request_token()

        # Verify request was made correctly
        mock_post.assert_called_once()
        call_args = mock_post.call_args

        assert call_args[0][0] == OpenSkyAuth.TOKEN_URL
        assert (
            call_args[1]["headers"]["Content-Type"]
            == "application/x-www-form-urlencoded"
        )

        data = call_args[1]["data"]
        assert data["grant_type"] == "client_credentials"
        assert data["client_id"] == "test-client-id"
        assert data["client_secret"] == "test-client-secret"

        # Verify response
        assert token_data == mock_token_response

    @patch("lara.tracking.auth.requests.post")
    def test_request_token_http_error(self, mock_post: Mock, credentials_file: str):
        """Test handling of HTTP errors during token request."""
        # Mock error response
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {
            "error": "invalid_client",
            "error_description": "Invalid credentials",
        }
        mock_post.return_value = mock_response

        auth = OpenSkyAuth(credentials_path=credentials_file)

        with pytest.raises(Exception, match="Token request failed with status 401"):
            auth._request_token()

    @patch("lara.tracking.auth.requests.post")
    def test_request_token_network_error(self, mock_post: Mock, credentials_file: str):
        """Test handling of network errors during token request."""
        import requests

        mock_post.side_effect = requests.exceptions.ConnectionError("Network error")

        auth = OpenSkyAuth(credentials_path=credentials_file)

        with pytest.raises(Exception, match="Failed to obtain access token"):
            auth._request_token()

    @patch("lara.tracking.auth.requests.post")
    def test_get_token_requests_new_token(
        self,
        mock_post: Mock,
        mock_token_response: Dict[str, Any],
        credentials_file: str,
        capsys,
    ):
        """Test that get_token requests new token when none exists."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_token_response
        mock_post.return_value = mock_response

        auth = OpenSkyAuth(credentials_path=credentials_file)
        token = auth.get_token()

        assert token == mock_token_response["access_token"]
        assert auth.access_token == mock_token_response["access_token"]
        assert auth.token_type == "Bearer"
        assert auth.token_expires_at is not None

        # Check console output
        captured = capsys.readouterr()
        assert "Access token obtained" in captured.out

    @patch("lara.tracking.auth.requests.post")
    def test_get_token_reuses_valid_token(
        self,
        mock_post: Mock,
        mock_token_response: Dict[str, Any],
        credentials_file: str,
    ):
        """Test that get_token reuses existing valid token."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_token_response
        mock_post.return_value = mock_response

        auth = OpenSkyAuth(credentials_path=credentials_file)

        # Get token first time
        token1 = auth.get_token()
        assert mock_post.call_count == 1

        # Get token second time - should not request new token
        token2 = auth.get_token()
        assert mock_post.call_count == 1  # Still only one call
        assert token1 == token2

    @patch("lara.tracking.auth.requests.post")
    def test_get_token_refreshes_expired_token(
        self,
        mock_post: Mock,
        mock_token_response: Dict[str, Any],
        credentials_file: str,
    ):
        """Test that get_token refreshes expired token."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_token_response
        mock_post.return_value = mock_response

        auth = OpenSkyAuth(credentials_path=credentials_file)

        # Get initial token
        auth.get_token()
        assert mock_post.call_count == 1

        # Manually expire token
        auth.token_expires_at = datetime.now() - timedelta(seconds=1)

        # Get token again - should refresh
        auth.get_token()
        assert mock_post.call_count == 2

    @patch("lara.tracking.auth.requests.post")
    def test_get_token_force_refresh(
        self,
        mock_post: Mock,
        mock_token_response: Dict[str, Any],
        credentials_file: str,
    ):
        """Test forced token refresh."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_token_response
        mock_post.return_value = mock_response

        auth = OpenSkyAuth(credentials_path=credentials_file)

        # Get initial token
        auth.get_token()
        assert mock_post.call_count == 1

        # Force refresh even though token is valid
        auth.get_token(force_refresh=True)
        assert mock_post.call_count == 2

    def test_is_token_valid_no_token(self, credentials_file: str):
        """Test token validation when no token exists."""
        auth = OpenSkyAuth(credentials_path=credentials_file)
        assert auth._is_token_valid() is False

    def test_is_token_valid_expired_token(self, credentials_file: str):
        """Test token validation with expired token."""
        auth = OpenSkyAuth(credentials_path=credentials_file)
        auth.access_token = "test-token"
        auth.token_expires_at = datetime.now() - timedelta(seconds=1)

        assert auth._is_token_valid() is False

    def test_is_token_valid_valid_token(self, credentials_file: str):
        """Test token validation with valid token."""
        auth = OpenSkyAuth(credentials_path=credentials_file)
        auth.access_token = "test-token"
        auth.token_expires_at = datetime.now() + timedelta(minutes=10)

        assert auth._is_token_valid() is True

    def test_invalidate_token(self, credentials_file: str):
        """Test token invalidation."""
        auth = OpenSkyAuth(credentials_path=credentials_file)
        auth.access_token = "test-token"
        auth.token_expires_at = datetime.now() + timedelta(minutes=10)

        auth.invalidate_token()

        assert auth.access_token is None
        assert auth.token_expires_at is None


# ============================================================================
# OpenSkyAuth Tests - API Integration
# ============================================================================


class TestOpenSkyAuthAPIIntegration:
    """Tests for API request methods and authentication headers."""

    @patch("lara.tracking.auth.requests.post")
    def test_get_auth_headers(
        self,
        mock_post: Mock,
        mock_token_response: Dict[str, Any],
        credentials_file: str,
    ):
        """Test authentication header generation."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_token_response
        mock_post.return_value = mock_response

        auth = OpenSkyAuth(credentials_path=credentials_file)
        headers = auth.get_auth_headers()

        assert "Authorization" in headers
        assert headers["Authorization"].startswith("Bearer ")
        assert mock_token_response["access_token"] in headers["Authorization"]

    @patch("lara.tracking.auth.requests.post")
    @patch("lara.tracking.auth.requests.get")
    def test_make_authenticated_request_success(
        self,
        mock_get: Mock,
        mock_post: Mock,
        mock_token_response: Dict[str, Any],
        credentials_file: str,
    ):
        """Test making authenticated API request."""
        # Mock token request
        mock_token_resp = Mock()
        mock_token_resp.status_code = 200
        mock_token_resp.json.return_value = mock_token_response
        mock_post.return_value = mock_token_resp

        # Mock API request
        mock_api_resp = Mock()
        mock_api_resp.status_code = 200
        mock_api_resp.json.return_value = {"states": []}
        mock_get.return_value = mock_api_resp

        auth = OpenSkyAuth(credentials_path=credentials_file)
        response = auth.make_authenticated_request(
            "https://opensky-network.org/api/states/all",
            params={"lamin": 49.0, "lomin": 8.0},
        )

        # Verify token was obtained
        assert mock_post.call_count == 1

        # Verify API request was made with auth header
        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args[1]
        assert "headers" in call_kwargs
        assert "Authorization" in call_kwargs["headers"]
        assert call_kwargs["params"] == {"lamin": 49.0, "lomin": 8.0}

        assert response.status_code == 200

    @patch("lara.tracking.auth.requests.post")
    @patch("lara.tracking.auth.requests.get")
    def test_make_authenticated_request_token_refresh_on_401(
        self,
        mock_get: Mock,
        mock_post: Mock,
        mock_token_response: Dict[str, Any],
        credentials_file: str,
        capsys,
    ):
        """Test automatic token refresh when API returns 401."""
        # Mock token requests
        mock_token_resp = Mock()
        mock_token_resp.status_code = 200
        mock_token_resp.json.return_value = mock_token_response
        mock_post.return_value = mock_token_resp

        # Mock API requests - first 401, then success
        mock_api_resp_401 = Mock()
        mock_api_resp_401.status_code = 401

        mock_api_resp_200 = Mock()
        mock_api_resp_200.status_code = 200
        mock_api_resp_200.json.return_value = {"states": []}

        mock_get.side_effect = [mock_api_resp_401, mock_api_resp_200]

        auth = OpenSkyAuth(credentials_path=credentials_file)
        response = auth.make_authenticated_request(
            "https://opensky-network.org/api/states/all"
        )

        # Should have called token endpoint twice (initial + refresh)
        assert mock_post.call_count == 2

        # Should have called API endpoint twice (401 + retry)
        assert mock_get.call_count == 2

        # Final response should be successful
        assert response.status_code == 200

        # Check console output for refresh message
        captured = capsys.readouterr()
        assert "Token expired during request" in captured.out

    @patch("lara.tracking.auth.requests.post")
    @patch("lara.tracking.auth.requests.get")
    def test_make_authenticated_request_timeout(
        self,
        mock_get: Mock,
        mock_post: Mock,
        mock_token_response: Dict[str, Any],
        credentials_file: str,
    ):
        """Test handling of request timeout."""
        import requests

        # Mock token request
        mock_token_resp = Mock()
        mock_token_resp.status_code = 200
        mock_token_resp.json.return_value = mock_token_response
        mock_post.return_value = mock_token_resp

        # Mock API timeout
        mock_get.side_effect = requests.exceptions.Timeout()

        auth = OpenSkyAuth(credentials_path=credentials_file)

        with pytest.raises(requests.exceptions.Timeout):
            auth.make_authenticated_request(
                "https://opensky-network.org/api/states/all", timeout=5
            )


# ============================================================================
# OpenSkyAuth Tests - Authentication Testing
# ============================================================================


class TestOpenSkyAuthTesting:
    """Tests for the test_authentication method."""

    @patch("lara.tracking.auth.requests.post")
    @patch("lara.tracking.auth.requests.get")
    def test_authentication_success(
        self,
        mock_get: Mock,
        mock_post: Mock,
        mock_token_response: Dict[str, Any],
        credentials_file: str,
        capsys,
    ):
        """Test successful authentication test."""
        # Mock token request
        mock_token_resp = Mock()
        mock_token_resp.status_code = 200
        mock_token_resp.json.return_value = mock_token_response
        mock_post.return_value = mock_token_resp

        # Mock API test request
        mock_api_resp = Mock()
        mock_api_resp.status_code = 200
        mock_get.return_value = mock_api_resp

        auth = OpenSkyAuth(credentials_path=credentials_file)
        result = auth.test_authentication()

        assert result is True

        captured = capsys.readouterr()
        assert "test successful" in captured.out

    @patch("lara.tracking.auth.requests.post")
    def test_authentication_failure_no_token(
        self, mock_post: Mock, credentials_file: str, capsys
    ):
        """Test authentication test when token request fails."""
        mock_post.side_effect = Exception("Network error")

        auth = OpenSkyAuth(credentials_path=credentials_file)
        result = auth.test_authentication()

        assert result is False

        captured = capsys.readouterr()
        assert "failed" in captured.out

    @patch("lara.tracking.auth.requests.post")
    @patch("lara.tracking.auth.requests.get")
    def test_authentication_failure_401(
        self,
        mock_get: Mock,
        mock_post: Mock,
        mock_token_response: Dict[str, Any],
        credentials_file: str,
        capsys,
    ):
        """Test authentication test when API returns 401."""
        # Mock token request
        mock_token_resp = Mock()
        mock_token_resp.status_code = 200
        mock_token_resp.json.return_value = mock_token_response
        mock_post.return_value = mock_token_resp

        # Mock API 401
        mock_api_resp = Mock()
        mock_api_resp.status_code = 401
        mock_get.return_value = mock_api_resp

        auth = OpenSkyAuth(credentials_path=credentials_file)
        result = auth.test_authentication()

        assert result is False

        captured = capsys.readouterr()
        assert "not accepted" in captured.out


# ============================================================================
# OpenSkyBasicAuth Tests
# ============================================================================


class TestOpenSkyBasicAuth:
    """Tests for fallback basic authentication."""

    def test_init(self):
        """Test basic auth initialization."""
        auth = OpenSkyBasicAuth("testuser", "testpass")

        assert auth.username == "testuser"
        assert auth.password == "testpass"
        assert auth.credentials == ("testuser", "testpass")
        assert auth.client_id == "testuser"  # For display

    @patch("lara.tracking.auth.requests.get")
    def test_make_authenticated_request(self, mock_get: Mock):
        """Test making request with basic auth."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"states": []}
        mock_get.return_value = mock_response

        auth = OpenSkyBasicAuth("testuser", "testpass")
        response = auth.make_authenticated_request(
            "https://opensky-network.org/api/states/all", params={"lamin": 49.0}
        )

        # Verify request was made with auth tuple
        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args[1]
        assert call_kwargs["auth"] == ("testuser", "testpass")
        assert call_kwargs["params"] == {"lamin": 49.0}

        assert response.status_code == 200

    @patch("lara.tracking.auth.requests.get")
    def test_authentication_success(self, mock_get: Mock, capsys):
        """Test successful basic authentication test."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        auth = OpenSkyBasicAuth("testuser", "testpass")
        result = auth.test_authentication()

        assert result is True

        captured = capsys.readouterr()
        assert "Basic authentication successful" in captured.out
        assert "deprecated" in captured.out

    @patch("lara.tracking.auth.requests.get")
    def test_authentication_failure(self, mock_get: Mock, capsys):
        """Test failed basic authentication test."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response

        auth = OpenSkyBasicAuth("testuser", "wrongpass")
        result = auth.test_authentication()

        assert result is False

        captured = capsys.readouterr()
        assert "failed" in captured.out


# ============================================================================
# Helper Function Tests
# ============================================================================


class TestCreateAuthFromConfig:
    """Tests for the create_auth_from_config helper function."""

    @patch("lara.tracking.auth.OpenSkyAuth")
    def test_create_with_credentials_path(self, mock_auth_class: Mock):
        """Test creating auth with credentials_path in config."""
        # Setup mock
        mock_auth_instance = Mock()
        mock_auth_instance.test_authentication.return_value = True
        mock_auth_class.return_value = mock_auth_instance

        # Setup config
        config = Mock()
        config.get = Mock(
            side_effect=lambda key, default=None: {
                "api.credentials_path": "credentials.json"
            }.get(key, default)
        )

        result = create_auth_from_config(config)

        assert result == mock_auth_instance
        mock_auth_class.assert_called_once_with(credentials_path="credentials.json")
        mock_auth_instance.test_authentication.assert_called_once()

    @patch("lara.tracking.auth.OpenSkyAuth")
    def test_create_with_client_credentials(self, mock_auth_class: Mock):
        """Test creating auth with direct client_id and client_secret."""
        mock_auth_instance = Mock()
        mock_auth_instance.test_authentication.return_value = True
        mock_auth_class.return_value = mock_auth_instance

        config = Mock()
        config.get = Mock(
            side_effect=lambda key, default=None: {
                "api.credentials_path": None,
                "api.client_id": "test-id",
                "api.client_secret": "test-secret",
            }.get(key, default)
        )

        result = create_auth_from_config(config)

        assert result == mock_auth_instance
        mock_auth_class.assert_called_once_with(
            client_id="test-id", client_secret="test-secret"
        )

    @patch("lara.tracking.auth.OpenSkyBasicAuth")
    def test_create_with_basic_auth(self, mock_auth_class: Mock, capsys):
        """Test creating auth with username/password (basic auth)."""
        mock_auth_instance = Mock()
        mock_auth_instance.test_authentication.return_value = True
        mock_auth_class.return_value = mock_auth_instance

        config = Mock()
        config.get = Mock(
            side_effect=lambda key, default=None: {
                "api.credentials_path": None,
                "api.client_id": None,
                "api.client_secret": None,
                "api.username": "testuser",
                "api.password": "testpass",
            }.get(key, default)
        )

        result = create_auth_from_config(config)

        assert result == mock_auth_instance
        mock_auth_class.assert_called_once_with("testuser", "testpass")

        captured = capsys.readouterr()
        assert "basic authentication" in captured.out

    def test_create_no_credentials_returns_none(self):
        """Test that None is returned when no credentials configured."""
        config = Mock()
        config.get = Mock(return_value=None)

        result = create_auth_from_config(config)

        assert result is None

    @patch("lara.tracking.auth.OpenSkyAuth")
    def test_create_auth_test_fails_returns_none(self, mock_auth_class: Mock, capsys):
        """Test that None is returned when authentication test fails."""
        mock_auth_instance = Mock()
        mock_auth_instance.test_authentication.return_value = False
        mock_auth_class.return_value = mock_auth_instance

        config = Mock()
        config.get = Mock(
            side_effect=lambda key, default=None: {
                "api.credentials_path": "credentials.json"
            }.get(key, default)
        )

        result = create_auth_from_config(config)

        assert result is None

        captured = capsys.readouterr()
        assert "test failed" in captured.out

    @patch("lara.tracking.auth.OpenSkyAuth")
    def test_create_auth_exception_returns_none(self, mock_auth_class: Mock, capsys):
        """Test that None is returned when auth initialization raises exception."""
        mock_auth_class.side_effect = Exception("Init failed")

        config = Mock()
        config.get = Mock(
            side_effect=lambda key, default=None: {
                "api.credentials_path": "credentials.json"
            }.get(key, default)
        )

        result = create_auth_from_config(config)

        assert result is None

        captured = capsys.readouterr()
        assert "initialization failed" in captured.out


# ============================================================================
# Integration Tests
# ============================================================================


class TestAuthIntegration:
    """Integration tests for authentication flow."""

    @patch("lara.tracking.auth.requests.post")
    @patch("lara.tracking.auth.requests.get")
    def test_full_authentication_flow(
        self, mock_get: Mock, mock_post: Mock, credentials_file: str
    ):
        """Test complete authentication and API request flow."""
        # Mock token response
        token_response = {
            "access_token": "test-access-token",
            "token_type": "Bearer",
            "expires_in": 1800,
        }
        mock_token_resp = Mock()
        mock_token_resp.status_code = 200
        mock_token_resp.json.return_value = token_response
        mock_post.return_value = mock_token_resp

        # Mock API response
        api_response = {"states": [["abc123", "TEST1", "Germany"]]}
        mock_api_resp = Mock()
        mock_api_resp.status_code = 200
        mock_api_resp.json.return_value = api_response
        mock_get.return_value = mock_api_resp

        # Create auth and make request
        auth = OpenSkyAuth(credentials_path=credentials_file)

        # First request
        response1 = auth.make_authenticated_request(
            "https://opensky-network.org/api/states/all", params={"lamin": 49.0}
        )

        # Second request (should reuse token)
        response2 = auth.make_authenticated_request(
            "https://opensky-network.org/api/states/all", params={"lamin": 49.0}
        )

        # Verify token was only requested once
        assert mock_post.call_count == 1

        # Verify both API requests succeeded
        assert mock_get.call_count == 2
        assert response1.status_code == 200
        assert response2.status_code == 200

    @patch("lara.tracking.auth.requests.post")
    @patch("lara.tracking.auth.requests.get")
    def test_token_expiry_and_refresh(
        self, mock_get: Mock, mock_post: Mock, credentials_file: str
    ):
        """Test that expired tokens are properly refreshed."""
        # Mock token responses
        token_response = {
            "access_token": "test-token",
            "token_type": "Bearer",
            "expires_in": 1800,
        }
        mock_token_resp = Mock()
        mock_token_resp.status_code = 200
        mock_token_resp.json.return_value = token_response
        mock_post.return_value = mock_token_resp

        # Mock API response
        mock_api_resp = Mock()
        mock_api_resp.status_code = 200
        mock_api_resp.json.return_value = {"states": []}
        mock_get.return_value = mock_api_resp

        auth = OpenSkyAuth(credentials_path=credentials_file)

        # First request
        auth.make_authenticated_request("https://opensky-network.org/api/states/all")
        assert mock_post.call_count == 1

        # Manually expire token
        auth.token_expires_at = datetime.now() - timedelta(seconds=1)

        # Second request should refresh token
        auth.make_authenticated_request("https://opensky-network.org/api/states/all")
        assert mock_post.call_count == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
