"""
Pytest configuration and fixtures for Prompt API tests
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
from database import get_db
from models import Base, User, Game, Prompt, PromptType
from auth import get_password_hash, create_access_token
from datetime import timedelta

# Use in-memory SQLite for tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"


def _create_test_default_data(db):
    """Create default system user, game, and prompts for tests"""
    from pathlib import Path

    # Create default system user
    system_user = User(username="system", email="system@example.com", hashed_password="dummy_hash")
    db.add(system_user)
    db.commit()
    db.refresh(system_user)

    # Create default game
    default_game = Game(name="default", created_by=system_user.id)
    db.add(default_game)
    db.commit()
    db.refresh(default_game)

    # Create default prompts from files if they exist
    prompts_dir = Path(__file__).parent.parent / "prompts"

    prompt_mappings = [
        (PromptType.SYSTEM, prompts_dir / "base_system_prompt.txt"),
        (PromptType.ORDER, prompts_dir / "order_instructions.txt"),
        (PromptType.NEGOTIATION, prompts_dir / "conversation_instructions.txt"),
    ]

    for prompt_type, file_path in prompt_mappings:
        content = "Default test content"  # Fallback content
        if file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
            except Exception:
                pass  # Use fallback content

        default_prompt = Prompt(
            game_id=default_game.id, user_id=None, prompt_type=prompt_type, content=content, version=1, is_default=True
        )
        db.add(default_prompt)

    db.commit()


@pytest.fixture(scope="function")
def test_db():
    """Create a fresh database for each test"""
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    db = TestingSessionLocal()
    try:
        # Create default data needed for tests
        _create_test_default_data(db)
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(test_db):
    """Create a test client with test database"""

    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def test_user(test_db):
    """Create a test user"""
    user = User(username="testuser", email="test@example.com", hashed_password=get_password_hash("password123"))
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def test_user2(test_db):
    """Create a second test user"""
    user = User(username="testuser2", email="test2@example.com", hashed_password=get_password_hash("password456"))
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def auth_token(test_user):
    """Create an authentication token for test user"""
    access_token = create_access_token(data={"sub": test_user.username}, expires_delta=timedelta(minutes=30))
    return access_token


@pytest.fixture
def auth_token2(test_user2):
    """Create an authentication token for second test user"""
    access_token = create_access_token(data={"sub": test_user2.username}, expires_delta=timedelta(minutes=30))
    return access_token


@pytest.fixture
def auth_headers(auth_token):
    """Create authorization headers"""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def auth_headers2(auth_token2):
    """Create authorization headers for second user"""
    return {"Authorization": f"Bearer {auth_token2}"}


@pytest.fixture
def test_game(test_db, test_user):
    """Create a test game"""
    game = Game(name="Test Game", created_by=test_user.id)
    test_db.add(game)
    test_db.commit()
    test_db.refresh(game)
    return game


@pytest.fixture
def test_default_prompt(test_db, test_game):
    """Create a default prompt"""
    prompt = Prompt(
        game_id=test_game.id,
        user_id=None,
        prompt_type=PromptType.ORDER,
        content="Default order instructions",
        version=1,
        is_default=True,
    )
    test_db.add(prompt)
    test_db.commit()
    test_db.refresh(prompt)
    return prompt


@pytest.fixture
def test_custom_prompt(test_db, test_game, test_user):
    """Create a custom user prompt"""
    prompt = Prompt(
        game_id=test_game.id,
        user_id=test_user.id,
        prompt_type=PromptType.ORDER,
        content="Custom order instructions",
        version=1,
        is_default=False,
    )
    test_db.add(prompt)
    test_db.commit()
    test_db.refresh(prompt)
    return prompt
