"""
Tests for health check endpoint
"""



class TestHealthEndpoint:
    """Test health check endpoint"""

    def test_health_check_success(self, client):
        """Test that health check returns success"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}

    def test_health_check_no_auth_required(self, client):
        """Test that health check doesn't require authentication"""
        # Even with invalid auth header, health check should work
        headers = {"Authorization": "Bearer invalid-token"}
        response = client.get("/health", headers=headers)
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}
