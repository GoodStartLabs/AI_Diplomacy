from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
from datetime import timedelta
from typing import List
import logging

from database import get_db, create_tables
from models import User, Game, Prompt, PromptType as DBPromptType
from schemas import UserCreate, UserResponse, UserLogin, Token, GameCreate, GameResponse, PromptCreate, PromptResponse, PromptType
from auth import authenticate_user, create_access_token, get_current_user, get_password_hash, ACCESS_TOKEN_EXPIRE_MINUTES

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Prompt API", description="API for managing game prompts with user authentication and versioning", version="1.0.0"
)

security = HTTPBearer()


@app.on_event("startup")
async def startup_event():
    """Create database tables on startup"""
    create_tables()
    logger.info("Database tables created")


# Authentication endpoints
@app.post("/auth/register", response_model=UserResponse)
def register(user: UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    # Check if user already exists
    db_user = db.query(User).filter((User.username == user.username) | (User.email == user.email)).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username or email already registered")

    # Create new user
    hashed_password = get_password_hash(user.password)
    db_user = User(username=user.username, email=user.email, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    logger.info(f"New user registered: {user.username}")
    return db_user


@app.post("/auth/login", response_model=Token)
def login(user_credentials: UserLogin, db: Session = Depends(get_db)):
    """Login user and return access token"""
    user = authenticate_user(db, user_credentials.username, user_credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)

    logger.info(f"User logged in: {user.username}")
    return {"access_token": access_token, "token_type": "bearer"}


# Game endpoints
@app.post("/games", response_model=GameResponse)
def create_game(game: GameCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Create a new game"""
    db_game = Game(name=game.name, created_by=current_user.id)
    db.add(db_game)
    db.commit()
    db.refresh(db_game)

    logger.info(f"New game created: {game.name} by user {current_user.username}")
    return db_game


@app.get("/games", response_model=List[GameResponse])
def list_games(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """List all games created by the current user"""
    games = db.query(Game).filter(Game.created_by == current_user.id).all()
    return games


# Prompt endpoints
@app.get("/prompt")
def get_prompt(
    game_id: int, prompt_type: PromptType, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get the latest prompt for a user, game, and prompt type"""

    # Verify game exists and user has access
    game = db.query(Game).filter(Game.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    # Convert schema enum to DB enum
    db_prompt_type = DBPromptType(prompt_type.value)

    # First, try to get user's custom prompt (latest version)
    user_prompt = (
        db.query(Prompt)
        .filter(and_(Prompt.game_id == game_id, Prompt.user_id == current_user.id, Prompt.prompt_type == db_prompt_type))
        .order_by(desc(Prompt.version))
        .first()
    )

    if user_prompt:
        logger.info(f"Retrieved custom prompt for user {current_user.username}, game {game_id}, type {prompt_type}")
        return PromptResponse.model_validate(user_prompt)

    # If no user prompt, get default prompt
    default_prompt = (
        db.query(Prompt)
        .filter(
            and_(
                Prompt.game_id == game_id,
                Prompt.user_id.is_(None),
                Prompt.prompt_type == db_prompt_type,
                Prompt.is_default is True,
            )
        )
        .first()
    )

    if default_prompt:
        logger.info(f"Retrieved default prompt for user {current_user.username}, game {game_id}, type {prompt_type}")
        return PromptResponse.model_validate(default_prompt)

    raise HTTPException(status_code=404, detail=f"No prompt found for game {game_id} and type {prompt_type}")


@app.post("/prompt", response_model=PromptResponse)
def create_prompt(prompt: PromptCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Create a new version of a prompt for the current user"""

    # Verify game exists
    game = db.query(Game).filter(Game.id == prompt.game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    # Convert schema enum to DB enum
    db_prompt_type = DBPromptType(prompt.prompt_type.value)

    # Get the current highest version for this user/game/type combination
    latest_prompt = (
        db.query(Prompt)
        .filter(and_(Prompt.game_id == prompt.game_id, Prompt.user_id == current_user.id, Prompt.prompt_type == db_prompt_type))
        .order_by(desc(Prompt.version))
        .first()
    )

    # Increment version number
    new_version = (latest_prompt.version + 1) if latest_prompt else 1

    # Create new prompt
    db_prompt = Prompt(
        game_id=prompt.game_id,
        user_id=current_user.id,
        prompt_type=db_prompt_type,
        content=prompt.content,
        version=new_version,
        is_default=False,
    )

    db.add(db_prompt)
    db.commit()
    db.refresh(db_prompt)

    logger.info(
        f"New prompt created: user {current_user.username}, game {prompt.game_id}, type {prompt.prompt_type}, version {new_version}"
    )
    return PromptResponse.model_validate(db_prompt)


@app.get("/prompt/history")
def get_prompt_history(
    game_id: int, prompt_type: PromptType, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get all versions of prompts for a user, game, and prompt type"""

    # Verify game exists
    game = db.query(Game).filter(Game.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    # Convert schema enum to DB enum
    db_prompt_type = DBPromptType(prompt_type.value)

    # Get all user prompts for this game/type
    prompts = (
        db.query(Prompt)
        .filter(and_(Prompt.game_id == game_id, Prompt.user_id == current_user.id, Prompt.prompt_type == db_prompt_type))
        .order_by(desc(Prompt.version))
        .all()
    )

    return [PromptResponse.model_validate(prompt) for prompt in prompts]


# Health check endpoint
@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
