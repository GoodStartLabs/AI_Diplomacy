"""
Tests for authentication endpoints
"""

from jose import jwt
from datetime import datetime, timedelta, timezone
import os

SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-this-in-production")
ALGORITHM = "HS256"


class TestAuthEndpoints:
    """Test authentication endpoints"""

    def test_register_success(self, client):
        """Test successful user registration"""
        response = client.post(
            "/auth/register", json={"username": "newuser", "email": "newuser@example.com", "password": "securepassword123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "newuser"
        assert data["email"] == "newuser@example.com"
        assert "id" in data
        assert "created_at" in data
        assert "hashed_password" not in data

    def test_register_duplicate_username(self, client, test_user):
        """Test registration with duplicate username"""
        response = client.post(
            "/auth/register", json={"username": test_user.username, "email": "different@example.com", "password": "password123"}
        )
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]

    def test_register_duplicate_email(self, client, test_user):
        """Test registration with duplicate email"""
        response = client.post(
            "/auth/register", json={"username": "differentuser", "email": test_user.email, "password": "password123"}
        )
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]

    def test_register_invalid_email(self, client):
        """Test registration with invalid email format"""
        response = client.post("/auth/register", json={"username": "newuser", "email": "not-an-email", "password": "password123"})
        assert response.status_code == 422
        assert "email" in str(response.json()["detail"])

    def test_register_missing_fields(self, client):
        """Test registration with missing required fields"""
        # Missing password
        response = client.post("/auth/register", json={"username": "newuser", "email": "newuser@example.com"})
        assert response.status_code == 422

        # Missing email
        response = client.post("/auth/register", json={"username": "newuser", "password": "password123"})
        assert response.status_code == 422

        # Missing username
        response = client.post("/auth/register", json={"email": "newuser@example.com", "password": "password123"})
        assert response.status_code == 422

    def test_login_success(self, client, test_user):
        """Test successful login"""
        response = client.post("/auth/login", json={"username": "testuser", "password": "password123"})
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

        # Verify token is valid
        payload = jwt.decode(data["access_token"], SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == test_user.username

    def test_login_invalid_username(self, client):
        """Test login with non-existent username"""
        response = client.post("/auth/login", json={"username": "nonexistent", "password": "password123"})
        assert response.status_code == 401
        assert "Incorrect username or password" in response.json()["detail"]

    def test_login_invalid_password(self, client, test_user):
        """Test login with wrong password"""
        response = client.post("/auth/login", json={"username": test_user.username, "password": "wrongpassword"})
        assert response.status_code == 401
        assert "Incorrect username or password" in response.json()["detail"]

    def test_login_missing_fields(self, client):
        """Test login with missing fields"""
        # Missing password
        response = client.post("/auth/login", json={"username": "testuser"})
        assert response.status_code == 422

        # Missing username
        response = client.post("/auth/login", json={"password": "password123"})
        assert response.status_code == 422

    def test_access_protected_endpoint_without_token(self, client):
        """Test accessing protected endpoint without token"""
        response = client.get("/games")
        assert response.status_code == 403
        assert response.json()["detail"] == "Not authenticated"

    def test_access_protected_endpoint_with_invalid_token(self, client):
        """Test accessing protected endpoint with invalid token"""
        headers = {"Authorization": "Bearer invalid-token"}
        response = client.get("/games", headers=headers)
        assert response.status_code == 401
        assert "Could not validate credentials" in response.json()["detail"]

    def test_access_protected_endpoint_with_expired_token(self, client, test_user):
        """Test accessing protected endpoint with expired token"""
        # Create an expired token
        past_time = datetime.now(timezone.utc) - timedelta(hours=1)
        payload = {"sub": test_user.username, "exp": past_time}
        expired_token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

        headers = {"Authorization": f"Bearer {expired_token}"}
        response = client.get("/games", headers=headers)
        assert response.status_code == 401
        assert "Could not validate credentials" in response.json()["detail"]

    def test_access_protected_endpoint_with_malformed_auth_header(self, client):
        """Test accessing protected endpoint with malformed authorization header"""
        # No Bearer prefix
        headers = {"Authorization": "just-a-token"}
        response = client.get("/games", headers=headers)
        assert response.status_code == 403

        # Wrong prefix
        headers = {"Authorization": "Token some-token"}
        response = client.get("/games", headers=headers)
        assert response.status_code == 403

    def test_token_contains_correct_claims(self, client, test_user):
        """Test that JWT token contains expected claims"""
        response = client.post("/auth/login", json={"username": "testuser", "password": "password123"})
        assert response.status_code == 200

        token = response.json()["access_token"]
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        assert "sub" in payload
        assert payload["sub"] == test_user.username
        assert "exp" in payload

        # Check expiration is in the future
        exp_timestamp = payload["exp"]
        exp_datetime = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
        assert exp_datetime > datetime.now(timezone.utc)
