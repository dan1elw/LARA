"""
Tests for authentication.
"""

import json
import pytest
from datetime import datetime, timedelta
from lara.tracking.auth import OpenSkyAuth


@pytest.fixture
def valid_token_response():
    return {
        "access_token": "test-access-token",
        "token_type": "Bearer",
        "expires_in": 1800,
    }


@pytest.fixture
def mock_post_success(mocker, valid_token_response):
    mock_resp = mocker.Mock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = valid_token_response

    return mocker.patch("requests.post", return_value=mock_resp)


@pytest.fixture
def mock_get_200(mocker):
    mock_resp = mocker.Mock()
    mock_resp.status_code = 200
    mock_resp.text = "OK"

    return mocker.patch("requests.get", return_value=mock_resp)


class TestOpenSkyInitilizationAndCredentials:
    """Tests for OpenSkyAuth initialization and credential loading."""

    def test_init_with_client_credentials(self):
        """Test initialization with direct client credentials."""
        auth = OpenSkyAuth(client_id="id", client_secret="secret")

        assert auth.client_id == "id"
        assert auth.client_secret == "secret"

    def test_init_without_credentials_raises(self):
        """Test initialization without any credentials raises ValueError."""
        with pytest.raises(ValueError):
            OpenSkyAuth()

    def test_load_credentials_from_file(self, tmp_path):
        """Test loading credentials from a JSON file."""
        creds = {
            "clientId": "file-id",
            "clientSecret": "file-secret",
        }
        path = tmp_path / "credentials.json"
        path.write_text(json.dumps(creds))

        auth = OpenSkyAuth(credentials_path=str(path))

        assert auth.client_id == "file-id"
        assert auth.client_secret == "file-secret"

    def test_load_credentials_missing_fields(self, tmp_path):
        """Test that missing fields in credentials file raises ValueError."""
        path = tmp_path / "credentials.json"
        path.write_text(json.dumps({"clientId": "only-id"}))

        with pytest.raises(ValueError):
            OpenSkyAuth(credentials_path=str(path))

    def test_load_credentials_file_not_found(self):
        """Test that missing credentials file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            OpenSkyAuth(credentials_path="does-not-exist.json")


class TestOpenSkyTokens:
    """Tests for OpenSkyAuth token management."""

    def test_get_token_fetches_and_caches(self, mock_post_success):
        """Test that get_token fetches and caches the token."""
        auth = OpenSkyAuth(client_id="id", client_secret="secret")

        token = auth.get_token()

        assert token == "test-access-token"
        assert auth.access_token == "test-access-token"
        assert auth.token_expires_at is not None
        assert mock_post_success.call_count == 1

    def test_get_token_uses_cached_token(self, mock_post_success):
        """Test that get_token uses cached token if valid."""
        auth = OpenSkyAuth(client_id="id", client_secret="secret")

        token1 = auth.get_token()
        token2 = auth.get_token()

        assert token1 == token2
        assert mock_post_success.call_count == 1

    def test_force_refresh_fetches_new_token(self, mock_post_success):
        """Test that force_refresh fetches a new token."""
        auth = OpenSkyAuth(client_id="id", client_secret="secret")

        auth.get_token()
        auth.get_token(force_refresh=True)

        assert mock_post_success.call_count == 2

    def test_is_token_valid_false_when_missing(self):
        """Test that is_token_valid returns False when no token is present."""
        auth = OpenSkyAuth(client_id="id", client_secret="secret")

        assert auth._is_token_valid() is False

    def test_is_token_valid_true(self):
        """Test that is_token_valid returns True for valid token."""
        auth = OpenSkyAuth(client_id="id", client_secret="secret")
        auth.access_token = "token"
        auth.token_expires_at = datetime.now() + timedelta(minutes=5)

        assert auth._is_token_valid() is True

    def test_is_token_valid_false_when_expired(self):
        """Test that is_token_valid returns False for expired token."""
        auth = OpenSkyAuth(client_id="id", client_secret="secret")
        auth.access_token = "token"
        auth.token_expires_at = datetime.now() - timedelta(seconds=1)

        assert auth._is_token_valid() is False


class TestOpenSkyAuthenticatedRequests:
    """Tests for OpenSkyAuth authenticated requests."""

    def test_get_auth_headers(self, mock_post_success):
        """Test that get_auth_headers returns correct headers."""
        auth = OpenSkyAuth(client_id="id", client_secret="secret")

        headers = auth.get_auth_headers()

        assert headers == {"Authorization": "Bearer test-access-token"}

    def test_make_authenticated_request_retries_on_401(
        self, mocker, valid_token_response
    ):
        """Test that make_authenticated_request retries on 401 response."""
        auth = OpenSkyAuth(client_id="id", client_secret="secret")

        # First token request
        mocker.patch(
            "requests.post",
            return_value=mocker.Mock(
                status_code=200, json=lambda: valid_token_response
            ),
        )

        resp_401 = mocker.Mock(status_code=401)
        resp_200 = mocker.Mock(status_code=200)

        get_mock = mocker.patch(
            "requests.get",
            side_effect=[resp_401, resp_200],
        )

        response = auth.make_authenticated_request("https://example.com")

        assert response.status_code == 200
        assert get_mock.call_count == 2
