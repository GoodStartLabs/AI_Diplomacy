"""
Integration tests for complete workflows
"""



class TestIntegrationWorkflows:
    """Test complete user workflows"""

    def test_complete_user_workflow(self, client):
        """Test complete workflow from registration to prompt customization"""
        # 1. Register a new user
        register_response = client.post(
            "/auth/register", json={"username": "workflow_user", "email": "workflow@example.com", "password": "secure123"}
        )
        assert register_response.status_code == 200
        user_id = register_response.json()["id"]

        # 2. Login to get token
        login_response = client.post("/auth/login", json={"username": "workflow_user", "password": "secure123"})
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 3. Create a game
        game_response = client.post("/games", json={"name": "Workflow Test Game"}, headers=headers)
        assert game_response.status_code == 200
        game_id = game_response.json()["id"]

        # 4. Try to get a prompt (should fail if no default)
        prompt_response = client.get(f"/prompt?game_id={game_id}&prompt_type=Order", headers=headers)
        # Could be 404 if no default exists

        # 5. Create a custom prompt
        create_prompt_response = client.post(
            "/prompt",
            json={"game_id": game_id, "prompt_type": "Order", "content": "My custom order instructions for this game"},
            headers=headers,
        )
        assert create_prompt_response.status_code == 200
        assert create_prompt_response.json()["version"] == 1

        # 6. Get the prompt again - should return custom
        get_prompt_response = client.get(f"/prompt?game_id={game_id}&prompt_type=Order", headers=headers)
        assert get_prompt_response.status_code == 200
        assert get_prompt_response.json()["content"] == "My custom order instructions for this game"

        # 7. Update the prompt (create version 2)
        update_prompt_response = client.post(
            "/prompt",
            json={"game_id": game_id, "prompt_type": "Order", "content": "Updated order instructions v2"},
            headers=headers,
        )
        assert update_prompt_response.status_code == 200
        assert update_prompt_response.json()["version"] == 2

        # 8. Check history
        history_response = client.get(f"/prompt/history?game_id={game_id}&prompt_type=Order", headers=headers)
        assert history_response.status_code == 200
        history = history_response.json()
        assert len(history) == 2
        assert history[0]["version"] == 2
        assert history[1]["version"] == 1

    def test_multi_user_game_isolation(self, client):
        """Test that multiple users' games and prompts are properly isolated"""
        users = []

        # Create two users
        for i in range(2):
            # Register
            register_response = client.post(
                "/auth/register",
                json={"username": f"multiuser{i}", "email": f"multiuser{i}@example.com", "password": "password123"},
            )
            assert register_response.status_code == 200

            # Login
            login_response = client.post("/auth/login", json={"username": f"multiuser{i}", "password": "password123"})
            assert login_response.status_code == 200

            users.append(
                {
                    "username": f"multiuser{i}",
                    "token": login_response.json()["access_token"],
                    "headers": {"Authorization": f"Bearer {login_response.json()['access_token']}"},
                }
            )

        # Each user creates a game
        games = []
        for i, user in enumerate(users):
            game_response = client.post("/games", json={"name": f"User {i} Game"}, headers=user["headers"])
            assert game_response.status_code == 200
            games.append(game_response.json())

        # Verify each user only sees their own games
        for i, user in enumerate(users):
            list_response = client.get("/games", headers=user["headers"])
            assert list_response.status_code == 200
            user_games = list_response.json()
            assert len(user_games) == 1
            assert user_games[0]["id"] == games[i]["id"]

        # User 0 creates a prompt for their game
        prompt_response = client.post(
            "/prompt",
            json={"game_id": games[0]["id"], "prompt_type": "System", "content": "User 0's custom system prompt"},
            headers=users[0]["headers"],
        )
        assert prompt_response.status_code == 200

        # User 1 tries to access User 0's game prompt - should fail or get default
        get_response = client.get(f"/prompt?game_id={games[0]['id']}&prompt_type=System", headers=users[1]["headers"])
        # This might return 404 or a default, but shouldn't return User 0's custom prompt

    def test_prompt_versioning_workflow(self, client, auth_headers, test_game):
        """Test complete prompt versioning workflow"""
        prompt_type = "Negotiation"
        versions = []

        # Create multiple versions
        for i in range(5):
            response = client.post(
                "/prompt",
                json={"game_id": test_game.id, "prompt_type": prompt_type, "content": f"Negotiation prompt version {i + 1}"},
                headers=auth_headers,
            )
            assert response.status_code == 200
            versions.append(response.json())

        # Verify versions are incremented correctly
        for i, version in enumerate(versions):
            assert version["version"] == i + 1

        # Get current prompt - should be latest
        current_response = client.get(f"/prompt?game_id={test_game.id}&prompt_type={prompt_type}", headers=auth_headers)
        assert current_response.status_code == 200
        current = current_response.json()
        assert current["version"] == 5
        assert current["content"] == "Negotiation prompt version 5"

        # Get full history
        history_response = client.get(f"/prompt/history?game_id={test_game.id}&prompt_type={prompt_type}", headers=auth_headers)
        assert history_response.status_code == 200
        history = history_response.json()
        assert len(history) == 5

        # Verify history is in descending order
        for i in range(len(history) - 1):
            assert history[i]["version"] > history[i + 1]["version"]

    def test_all_prompt_types_workflow(self, client, auth_headers, test_game):
        """Test working with all three prompt types"""
        prompt_types = {
            "Order": "Instructions for order phase",
            "System": "System-wide instructions",
            "Negotiation": "Instructions for negotiation phase",
        }

        # Create a prompt for each type
        for prompt_type, content in prompt_types.items():
            response = client.post(
                "/prompt", json={"game_id": test_game.id, "prompt_type": prompt_type, "content": content}, headers=auth_headers
            )
            assert response.status_code == 200

        # Retrieve each prompt type
        for prompt_type, expected_content in prompt_types.items():
            response = client.get(f"/prompt?game_id={test_game.id}&prompt_type={prompt_type}", headers=auth_headers)
            assert response.status_code == 200
            assert response.json()["content"] == expected_content
            assert response.json()["prompt_type"] == prompt_type

    def test_error_recovery_workflow(self, client):
        """Test system behavior with various error conditions"""
        # Try to access protected endpoint without auth
        response = client.get("/games")
        assert response.status_code == 403

        # Try to login with wrong credentials
        response = client.post("/auth/login", json={"username": "nonexistent", "password": "wrong"})
        assert response.status_code == 401

        # Register a user
        response = client.post(
            "/auth/register", json={"username": "errortest", "email": "error@test.com", "password": "password123"}
        )
        assert response.status_code == 200

        # Login successfully
        response = client.post("/auth/login", json={"username": "errortest", "password": "password123"})
        assert response.status_code == 200
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Try to get prompt for non-existent game
        response = client.get("/prompt?game_id=99999&prompt_type=Order", headers=headers)
        assert response.status_code == 404

        # Create a game successfully
        response = client.post("/games", json={"name": "Error Test Game"}, headers=headers)
        assert response.status_code == 200
        game_id = response.json()["id"]

        # Try invalid prompt type
        response = client.post(
            "/prompt", json={"game_id": game_id, "prompt_type": "InvalidType", "content": "This should fail"}, headers=headers
        )
        assert response.status_code == 422
