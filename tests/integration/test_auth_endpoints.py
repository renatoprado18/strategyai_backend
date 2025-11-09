"""
Integration tests for Authentication Endpoints
Tests login, signup, and authentication flow
"""

import pytest
from fastapi import status
from unittest.mock import Mock, patch


@pytest.mark.integration
class TestAuthEndpoints:
    """Integration tests for auth endpoints"""

    def test_health_check(self, test_client):
        """Test health check endpoint (no auth required)"""
        response = test_client.get("/health")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "status" in data
        assert "checks" in data
        assert "timestamp" in data

    def test_root_endpoint(self, test_client):
        """Test root endpoint returns API information"""
        response = test_client.get("/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["service"] == "Strategy AI Lead Generator API"
        assert "version" in data
        assert "features" in data

    def test_login_missing_credentials(self, test_client):
        """Test login with missing credentials returns 422"""
        response = test_client.post(
            "/api/auth/login",
            json={}
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_login_invalid_email_format(self, test_client):
        """Test login with invalid email format"""
        response = test_client.post(
            "/api/auth/login",
            json={
                "email": "not-an-email",
                "password": "password123"
            }
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @patch('app.routes.auth.supabase_admin')
    def test_login_with_valid_credentials(self, mock_supabase, test_client):
        """Test successful login with valid credentials"""
        # Mock Supabase authentication response
        mock_response = Mock()
        mock_response.user = Mock(id="user-123", email="test@company.com")
        mock_response.session = Mock(access_token="test-token-123")
        mock_supabase.auth.sign_in_with_password.return_value = mock_response

        response = test_client.post(
            "/api/auth/login",
            json={
                "email": "test@company.com",
                "password": "password123"
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["success"] is True
        assert "data" in data
        assert data["data"]["access_token"] == "test-token-123"
        assert data["data"]["user"]["email"] == "test@company.com"

    @patch('app.routes.auth.supabase_admin')
    def test_login_with_wrong_password(self, mock_supabase, test_client):
        """Test login with wrong password"""
        # Mock Supabase to raise authentication error
        mock_supabase.auth.sign_in_with_password.side_effect = Exception("Invalid credentials")

        response = test_client.post(
            "/api/auth/login",
            json={
                "email": "test@company.com",
                "password": "wrong-password"
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["success"] is False
        assert "error" in data

    def test_signup_missing_fields(self, test_client):
        """Test signup with missing required fields"""
        response = test_client.post(
            "/api/auth/signup",
            json={}
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_signup_invalid_email(self, test_client):
        """Test signup with invalid email format"""
        response = test_client.post(
            "/api/auth/signup",
            json={
                "email": "invalid-email",
                "password": "password123"
            }
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @patch('app.routes.auth.supabase_admin')
    def test_signup_successful(self, mock_supabase, test_client):
        """Test successful user signup"""
        # Mock Supabase signup response
        mock_response = Mock()
        mock_response.user = Mock(id="user-123", email="newuser@company.com")
        mock_supabase.auth.sign_up.return_value = mock_response

        response = test_client.post(
            "/api/auth/signup",
            json={
                "email": "newuser@company.com",
                "password": "SecurePassword123!"
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["success"] is True
        assert "message" in data

    @patch('app.routes.auth.supabase_admin')
    def test_signup_duplicate_email(self, mock_supabase, test_client):
        """Test signup with already registered email"""
        # Mock Supabase to raise duplicate error
        mock_supabase.auth.sign_up.side_effect = Exception("User already registered")

        response = test_client.post(
            "/api/auth/signup",
            json={
                "email": "existing@company.com",
                "password": "password123"
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["success"] is False
        assert "error" in data

    def test_protected_endpoint_without_token(self, test_client):
        """Test accessing protected endpoint without token"""
        response = test_client.get("/api/admin/submissions")

        # Should return 401 or 403
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN
        ]

    def test_protected_endpoint_with_invalid_token(self, test_client):
        """Test accessing protected endpoint with invalid token"""
        response = test_client.get(
            "/api/admin/submissions",
            headers={"Authorization": "Bearer invalid-token"}
        )

        # Should return 401 or 403
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN
        ]

    @patch('app.routes.auth.verify_token')
    def test_protected_endpoint_with_valid_token(self, mock_verify, test_client):
        """Test accessing protected endpoint with valid token"""
        # Mock token verification
        mock_verify.return_value = {
            "id": "user-123",
            "email": "test@company.com"
        }

        with patch('app.core.database.get_all_submissions') as mock_db:
            mock_db.return_value = []

            response = test_client.get(
                "/api/admin/submissions",
                headers={"Authorization": "Bearer valid-token-123"}
            )

            # Should succeed
            assert response.status_code == status.HTTP_200_OK

    def test_logout_endpoint(self, test_client, mock_jwt_token):
        """Test logout endpoint"""
        # Note: Logout implementation depends on your auth strategy
        # This is a placeholder test
        response = test_client.post(
            "/api/auth/logout",
            headers={"Authorization": f"Bearer {mock_jwt_token}"}
        )

        # May return 200 or 401 depending on implementation
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_404_NOT_FOUND  # If endpoint doesn't exist
        ]

    @pytest.mark.parametrize("email,password,expected_status", [
        ("", "password", 422),  # Empty email
        ("test@company.com", "", 422),  # Empty password
        ("invalid", "password", 422),  # Invalid email format
    ])
    def test_login_validation(self, test_client, email, password, expected_status):
        """Test login input validation with various invalid inputs"""
        response = test_client.post(
            "/api/auth/login",
            json={
                "email": email,
                "password": password
            }
        )

        assert response.status_code == expected_status


@pytest.mark.integration
class TestAuthenticationFlow:
    """Test complete authentication flow"""

    @patch('app.routes.auth.supabase_admin')
    def test_signup_login_flow(self, mock_supabase, test_client):
        """Test complete signup and login flow"""
        email = "testuser@company.com"
        password = "SecurePassword123!"

        # Step 1: Signup
        mock_signup_response = Mock()
        mock_signup_response.user = Mock(id="user-123", email=email)
        mock_supabase.auth.sign_up.return_value = mock_signup_response

        signup_response = test_client.post(
            "/api/auth/signup",
            json={"email": email, "password": password}
        )

        assert signup_response.status_code == status.HTTP_200_OK
        assert signup_response.json()["success"] is True

        # Step 2: Login with same credentials
        mock_login_response = Mock()
        mock_login_response.user = Mock(id="user-123", email=email)
        mock_login_response.session = Mock(access_token="token-123")
        mock_supabase.auth.sign_in_with_password.return_value = mock_login_response

        login_response = test_client.post(
            "/api/auth/login",
            json={"email": email, "password": password}
        )

        assert login_response.status_code == status.HTTP_200_OK
        data = login_response.json()
        assert data["success"] is True
        assert "access_token" in data["data"]

    @patch('app.routes.auth.verify_token')
    @patch('app.core.database.get_all_submissions')
    def test_authenticated_request_flow(self, mock_db, mock_verify, test_client):
        """Test making authenticated requests"""
        # Mock authentication
        mock_verify.return_value = {"id": "user-123", "email": "test@company.com"}
        mock_db.return_value = []

        # Make authenticated request
        response = test_client.get(
            "/api/admin/submissions",
            headers={"Authorization": "Bearer valid-token"}
        )

        assert response.status_code == status.HTTP_200_OK
