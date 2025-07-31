# Prompt API

A FastAPI-based service for managing game prompts with user authentication and versioning.

## Features

- **User Authentication**: JWT-based authentication system
- **Prompt Management**: Create, retrieve, and version prompts per user and game
- **Prompt Types**: Support for Order, System, and Negotiation prompt types
- **Default Prompts**: Fallback to default prompts when users haven't created custom ones
- **Version Control**: Automatic versioning of prompt changes
- **PostgreSQL Backend**: Persistent storage with proper data relationships

## API Endpoints

### Authentication
- `POST /auth/register` - Register a new user
- `POST /auth/login` - Login and get access token

### Games
- `POST /games` - Create a new game
- `GET /games` - List user's games

### Prompts
- `GET /prompt?game_id={id}&prompt_type={type}` - Get latest prompt for user/game/type
- `POST /prompt` - Create new prompt version
- `GET /prompt/history?game_id={id}&prompt_type={type}` - Get prompt history

### Health
- `GET /health` - Health check endpoint

## Quick Start with Docker Compose

1. **Start the services**:
   ```bash
   docker-compose up prompt-db prompt-api
   ```

2. **Run migrations** (first time only):
   ```bash
   docker-compose exec prompt-api python migrate_prompts.py
   ```

3. **Access the API**:
   - API: http://localhost:8000
   - Docs: http://localhost:8000/docs
   - Database: localhost:5432

## Usage Example

1. **Register a user**:
   ```bash
   curl -X POST "http://localhost:8000/auth/register" \
     -H "Content-Type: application/json" \
     -d '{"username": "testuser", "email": "test@example.com", "password": "password123"}'
   ```

2. **Login**:
   ```bash
   curl -X POST "http://localhost:8000/auth/login" \
     -H "Content-Type: application/json" \
     -d '{"username": "testuser", "password": "password123"}'
   ```

3. **Create a game**:
   ```bash
   curl -X POST "http://localhost:8000/games" \
     -H "Authorization: Bearer YOUR_TOKEN_HERE" \
     -H "Content-Type: application/json" \
     -d '{"name": "My Game"}'
   ```

4. **Get a prompt** (will return default if no custom prompt exists):
   ```bash
   curl "http://localhost:8000/prompt?game_id=1&prompt_type=Order" \
     -H "Authorization: Bearer YOUR_TOKEN_HERE"
   ```

5. **Create a custom prompt**:
   ```bash
   curl -X POST "http://localhost:8000/prompt" \
     -H "Authorization: Bearer YOUR_TOKEN_HERE" \
     -H "Content-Type: application/json" \
     -d '{"game_id": 1, "prompt_type": "Order", "content": "Your custom prompt text here"}'
   ```

## Environment Variables

See `.env.example` for required environment variables.

## Development

To run locally for development:

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set up environment variables

3. Run the server:
   ```bash
   uvicorn main:app --reload
   ```