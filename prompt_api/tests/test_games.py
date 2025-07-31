"""
Tests for game endpoints
"""


class TestGameEndpoints:
    """Test game-related endpoints"""

    def test_create_game_success(self, client, auth_headers):
        """Test successful game creation"""
        response = client.post("/games", json={"name": "My New Game"}, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "My New Game"
        assert "id" in data
        assert "created_by" in data
        assert "created_at" in data

    def test_create_game_without_auth(self, client):
        """Test creating game without authentication"""
        response = client.post("/games", json={"name": "My New Game"})
        assert response.status_code == 403
        assert response.json()["detail"] == "Not authenticated"

    def test_create_game_empty_name(self, client, auth_headers):
        """Test creating game with empty name"""
        response = client.post("/games", json={"name": ""}, headers=auth_headers)
        # Empty string is technically valid - might want to add validation
        assert response.status_code == 200

    def test_create_game_missing_name(self, client, auth_headers):
        """Test creating game without name field"""
        response = client.post("/games", json={}, headers=auth_headers)
        assert response.status_code == 422

    def test_create_game_long_name(self, client, auth_headers):
        """Test creating game with very long name"""
        long_name = "A" * 2000  # Exceeds 100 char limit in model
        response = client.post("/games", json={"name": long_name}, headers=auth_headers)
        # This should fail due to database constraint
        assert response.status_code == 500 or response.status_code == 422

    def test_list_games_success(self, client, auth_headers, test_game):
        """Test listing user's games"""
        response = client.get("/games", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(game["id"] == test_game.id for game in data)

    def test_list_games_empty(self, client, auth_headers2):
        """Test listing games when user has none"""
        response = client.get("/games", headers=auth_headers2)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_list_games_without_auth(self, client):
        """Test listing games without authentication"""
        response = client.get("/games")
        assert response.status_code == 403
        assert response.json()["detail"] == "Not authenticated"

    def test_list_games_only_shows_own_games(self, client, auth_headers, auth_headers2):
        """Test that users only see their own games"""
        # Create games for both users
        response1 = client.post("/games", json={"name": "User1 Game"}, headers=auth_headers)
        assert response1.status_code == 200
        game1_id = response1.json()["id"]

        response2 = client.post("/games", json={"name": "User2 Game"}, headers=auth_headers2)
        assert response2.status_code == 200
        game2_id = response2.json()["id"]

        # User 1 should only see their game
        response = client.get("/games", headers=auth_headers)
        assert response.status_code == 200
        games = response.json()
        game_ids = [g["id"] for g in games]
        assert game1_id in game_ids
        assert game2_id not in game_ids

        # User 2 should only see their game
        response = client.get("/games", headers=auth_headers2)
        assert response.status_code == 200
        games = response.json()
        game_ids = [g["id"] for g in games]
        assert game1_id not in game_ids
        assert game2_id in game_ids

    def test_create_multiple_games_same_name(self, client, auth_headers):
        """Test creating multiple games with the same name"""
        # This should be allowed - games can have duplicate names
        response1 = client.post("/games", json={"name": "Duplicate Name"}, headers=auth_headers)
        assert response1.status_code == 200

        response2 = client.post("/games", json={"name": "Duplicate Name"}, headers=auth_headers)
        assert response2.status_code == 200

        # Both should have different IDs
        assert response1.json()["id"] != response2.json()["id"]

    def test_game_response_format(self, client, auth_headers):
        """Test that game response has correct format"""
        response = client.post("/games", json={"name": "Format Test Game"}, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()

        # Check all expected fields are present
        required_fields = ["id", "name", "created_by", "created_at"]
        for field in required_fields:
            assert field in data

        # Check field types
        assert isinstance(data["id"], int)
        assert isinstance(data["name"], str)
        assert isinstance(data["created_by"], int)
        assert isinstance(data["created_at"], str)

        # Check created_at is valid ISO format
        from datetime import datetime

        datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))
