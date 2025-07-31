#!/usr/bin/env python3
"""
Migration script to populate default prompts from existing files
"""

from pathlib import Path
from sqlalchemy.orm import Session

# Import local modules
from database import SessionLocal
from models import User, Game, Prompt, PromptType


def read_prompt_file(file_path: str) -> str:
    """Read content from a prompt file"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        print(f"Warning: File not found: {file_path}")
        return ""
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return ""


def create_default_game_and_user(db: Session) -> tuple[User, Game]:
    """Create a default user and game for storing default prompts"""

    # Check if default user already exists
    default_user = db.query(User).filter(User.username == "system").first()
    if not default_user:
        default_user = User(
            username="system",
            email="system@example.com",
            hashed_password="dummy_hash",  # System user doesn't need real auth
        )
        db.add(default_user)
        db.commit()
        db.refresh(default_user)
        print("Created default system user")

    # Check if default game already exists
    default_game = db.query(Game).filter(Game.name == "default").first()
    if not default_game:
        default_game = Game(name="default", created_by=default_user.id)
        db.add(default_game)
        db.commit()
        db.refresh(default_game)
        print("Created default game")

    return default_user, default_game


def migrate_prompts():
    """Main migration function"""
    print("Starting prompt migration...")

    # Create database tables first
    from database import create_tables

    create_tables()
    print("Database tables created")

    # Create database session
    db = SessionLocal()

    try:
        # Create default user and game
        default_user, default_game = create_default_game_and_user(db)

        # Base path for prompts (mounted from host)
        base_path = Path("./prompts")

        # Define prompt mappings: (prompt_type, file_paths)
        prompt_mappings = [
            # System prompts
            (
                PromptType.SYSTEM,
                [
                    base_path / "base_system_prompt.txt",
                ],
            ),
            # Order prompts
            (
                PromptType.ORDER,
                [
                    base_path / "order_instructions.txt",
                ],
            ),
            # Negotiation prompts
            (
                PromptType.NEGOTIATION,
                [
                    base_path / "conversation_instructions.txt",
                ],
            ),
        ]

        # Process each prompt type
        for prompt_type, file_paths in prompt_mappings:
            print(f"\nProcessing {prompt_type.value} prompts...")

            for file_path in file_paths:
                if file_path.exists():
                    # Check if this prompt already exists
                    existing_prompt = (
                        db.query(Prompt)
                        .filter(
                            Prompt.game_id == default_game.id,
                            Prompt.user_id.is_(None),
                            Prompt.prompt_type == prompt_type,
                            Prompt.is_default == True,
                        )
                        .first()
                    )

                    if existing_prompt:
                        print(f"  Skipping existing prompt: {file_path.name}")
                        continue

                    # Read file content
                    content = read_prompt_file(str(file_path))
                    if not content:
                        continue

                    # Create new default prompt
                    new_prompt = Prompt(
                        game_id=default_game.id,
                        user_id=None,  # NULL for default prompts
                        prompt_type=prompt_type,
                        content=content,
                        version=1,
                        is_default=True,
                    )

                    db.add(new_prompt)
                    print(f"  Added default prompt: {file_path.name}")
                else:
                    print(f"  Warning: File not found: {file_path}")

        # Commit all changes
        db.commit()
        print("\nMigration completed successfully!")

        # Print summary
        prompt_count = db.query(Prompt).filter(Prompt.is_default == True).count()
        print(f"Total default prompts in database: {prompt_count}")

    except Exception as e:
        print(f"Error during migration: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    migrate_prompts()
