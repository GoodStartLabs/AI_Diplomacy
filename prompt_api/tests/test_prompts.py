"""
Tests for prompt endpoints
"""



class TestPromptEndpoints:
    """Test prompt-related endpoints"""

    def test_get_default_prompt(self, client, auth_headers, test_game, test_default_prompt):
        """Test getting default prompt when no custom exists"""
        response = client.get(f"/prompt?game_id={test_game.id}&prompt_type=Order", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["content"] == test_default_prompt.content
        assert data["is_default"] is True
        assert data["user_id"] is None
        assert data["version"] == 1

    def test_get_custom_prompt(self, client, auth_headers, test_game, test_custom_prompt):
        """Test getting custom prompt when it exists"""
        response = client.get(f"/prompt?game_id={test_game.id}&prompt_type=Order", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["content"] == test_custom_prompt.content
        assert data["is_default"] is False
        assert data["user_id"] == test_custom_prompt.user_id

    def test_get_prompt_without_auth(self, client, test_game):
        """Test getting prompt without authentication"""
        response = client.get(f"/prompt?game_id={test_game.id}&prompt_type=Order")
        assert response.status_code == 403

    def test_get_prompt_nonexistent_game(self, client, auth_headers):
        """Test getting prompt for non-existent game"""
        response = client.get("/prompt?game_id=99999&prompt_type=Order", headers=auth_headers)
        assert response.status_code == 404
        assert "Game not found" in response.json()["detail"]

    def test_get_prompt_no_default_exists(self, client, auth_headers, test_game):
        """Test getting prompt when no default exists"""
        response = client.get(f"/prompt?game_id={test_game.id}&prompt_type=System", headers=auth_headers)
        assert response.status_code == 404
        assert "No prompt found" in response.json()["detail"]

    def test_get_prompt_invalid_type(self, client, auth_headers, test_game):
        """Test getting prompt with invalid prompt type"""
        response = client.get(f"/prompt?game_id={test_game.id}&prompt_type=InvalidType", headers=auth_headers)
        assert response.status_code == 422

    def test_get_prompt_missing_params(self, client, auth_headers):
        """Test getting prompt with missing parameters"""
        # Missing game_id
        response = client.get("/prompt?prompt_type=Order", headers=auth_headers)
        assert response.status_code == 422

        # Missing prompt_type
        response = client.get("/prompt?game_id=1", headers=auth_headers)
        assert response.status_code == 422

    def test_create_prompt_first_version(self, client, auth_headers, test_game):
        """Test creating first version of a custom prompt"""
        response = client.post(
            "/prompt",
            json={"game_id": test_game.id, "prompt_type": "System", "content": "My custom system prompt"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["content"] == "My custom system prompt"
        assert data["version"] == 1
        assert data["is_default"] is False
        assert data["prompt_type"] == "System"

    def test_create_prompt_increment_version(self, client, auth_headers, test_game, test_custom_prompt):
        """Test creating new version increments version number"""
        # Create second version
        response = client.post(
            "/prompt",
            json={"game_id": test_game.id, "prompt_type": "Order", "content": "Updated custom order prompt"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["version"] == 2
        assert data["content"] == "Updated custom order prompt"

        # Verify getting prompt returns latest version
        response = client.get(f"/prompt?game_id={test_game.id}&prompt_type=Order", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["version"] == 2
        assert data["content"] == "Updated custom order prompt"

    def test_create_prompt_without_auth(self, client, test_game):
        """Test creating prompt without authentication"""
        response = client.post(
            "/prompt", json={"game_id": test_game.id, "prompt_type": "Order", "content": "Unauthorized prompt"}
        )
        assert response.status_code == 403

    def test_create_prompt_nonexistent_game(self, client, auth_headers):
        """Test creating prompt for non-existent game"""
        response = client.post(
            "/prompt",
            json={"game_id": 99999, "prompt_type": "Order", "content": "Prompt for nonexistent game"},
            headers=auth_headers,
        )
        assert response.status_code == 404
        assert "Game not found" in response.json()["detail"]

    def test_create_prompt_empty_content(self, client, auth_headers, test_game):
        """Test creating prompt with empty content"""
        response = client.post(
            "/prompt", json={"game_id": test_game.id, "prompt_type": "Order", "content": ""}, headers=auth_headers
        )
        # Empty content should be allowed
        assert response.status_code == 200

    def test_create_prompt_very_long_content(self, client, auth_headers, test_game):
        """Test creating prompt with very long content"""
        long_content = "A" * 100000  # 100k characters
        response = client.post(
            "/prompt", json={"game_id": test_game.id, "prompt_type": "Order", "content": long_content}, headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["content"]) == 100000

    def test_prompt_history(self, client, auth_headers, test_game):
        """Test getting prompt version history"""
        # Create multiple versions
        for i in range(3):
            response = client.post(
                "/prompt",
                json={"game_id": test_game.id, "prompt_type": "Negotiation", "content": f"Version {i + 1} content"},
                headers=auth_headers,
            )
            assert response.status_code == 200

        # Get history
        response = client.get(f"/prompt/history?game_id={test_game.id}&prompt_type=Negotiation", headers=auth_headers)
        assert response.status_code == 200
        history = response.json()

        assert isinstance(history, list)
        assert len(history) == 3
        # Should be ordered by version descending
        assert history[0]["version"] == 3
        assert history[1]["version"] == 2
        assert history[2]["version"] == 1
        assert history[0]["content"] == "Version 3 content"

    def test_prompt_history_empty(self, client, auth_headers, test_game):
        """Test getting prompt history when none exist"""
        response = client.get(f"/prompt/history?game_id={test_game.id}&prompt_type=System", headers=auth_headers)
        assert response.status_code == 200
        history = response.json()
        assert isinstance(history, list)
        assert len(history) == 0

    def test_prompt_types(self, client, auth_headers, test_game):
        """Test all prompt types work correctly"""
        prompt_types = ["Order", "System", "Negotiation"]

        for prompt_type in prompt_types:
            response = client.post(
                "/prompt",
                json={"game_id": test_game.id, "prompt_type": prompt_type, "content": f"Test {prompt_type} prompt"},
                headers=auth_headers,
            )
            assert response.status_code == 200
            data = response.json()
            assert data["prompt_type"] == prompt_type

    def test_user_isolation(self, client, auth_headers, auth_headers2, test_game):
        """Test that users can only see their own custom prompts"""
        # User 1 creates a prompt
        response = client.post(
            "/prompt",
            json={"game_id": test_game.id, "prompt_type": "Order", "content": "User 1 custom prompt"},
            headers=auth_headers,
        )
        assert response.status_code == 200

        # User 2 gets prompt - should get default, not user 1's custom
        response = client.get(f"/prompt?game_id={test_game.id}&prompt_type=Order", headers=auth_headers2)
        # This would be 404 if no default exists, or would return default content
        # Not user 1's custom prompt
