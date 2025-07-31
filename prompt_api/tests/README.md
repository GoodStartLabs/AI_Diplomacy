# Prompt API Tests

Comprehensive test suite for the Prompt API covering authentication, game management, and prompt versioning.

## Test Structure

- `conftest.py` - Pytest configuration and shared fixtures
- `test_auth.py` - Authentication endpoint tests
- `test_games.py` - Game management endpoint tests
- `test_prompts.py` - Prompt CRUD and versioning tests
- `test_integration.py` - End-to-end workflow tests
- `test_health.py` - Health check endpoint tests

## Running Tests

### Run all tests:
```bash
python -m pytest
```

### Run specific test file:
```bash
python -m pytest tests/test_auth.py -v
```

### Run with coverage:
```bash
python -m pytest --cov=. --cov-report=html
```

### Use the convenience script:
```bash
./run_tests.sh           # Run all tests
./run_tests.sh auth      # Run auth tests only
./run_tests.sh games     # Run game tests only
./run_tests.sh prompts   # Run prompt tests only
./run_tests.sh integration # Run integration tests only
./run_tests.sh coverage  # Run with coverage report
```

## Test Coverage

The test suite covers:

### Authentication Tests (`test_auth.py`)
- ✅ User registration (success and failures)
- ✅ User login (success and failures)
- ✅ Duplicate username/email handling
- ✅ Invalid credentials handling
- ✅ JWT token validation
- ✅ Expired token handling
- ✅ Protected endpoint access

### Game Tests (`test_games.py`)
- ✅ Game creation
- ✅ Game listing
- ✅ User isolation (users only see their own games)
- ✅ Authorization requirements
- ✅ Input validation

### Prompt Tests (`test_prompts.py`)
- ✅ Getting default prompts
- ✅ Creating custom prompts
- ✅ Version incrementation
- ✅ Getting latest version
- ✅ Prompt history
- ✅ All prompt types (Order, System, Negotiation)
- ✅ User isolation
- ✅ Game validation
- ✅ Edge cases (empty content, very long content)

### Integration Tests (`test_integration.py`)
- ✅ Complete user workflow
- ✅ Multi-user isolation
- ✅ Prompt versioning workflow
- ✅ Error recovery
- ✅ All prompt types workflow

## Common Test Scenarios

### Registration Failures
- Duplicate username
- Duplicate email
- Invalid email format
- Missing required fields

### Authentication Failures
- Invalid username
- Wrong password
- Expired token
- Malformed token
- Missing authorization header

### Game Operation Failures
- Creating game without auth
- Accessing non-existent game
- Cross-user access attempts

### Prompt Operation Failures
- Getting prompt for non-existent game
- Creating prompt without auth
- Invalid prompt type
- Missing required parameters

## Fixtures

Key fixtures provided by `conftest.py`:
- `client` - FastAPI test client
- `test_db` - In-memory test database
- `test_user` - Pre-created test user
- `auth_token` - Valid JWT token
- `auth_headers` - Authorization headers
- `test_game` - Pre-created test game
- `test_default_prompt` - Default prompt fixture
- `test_custom_prompt` - Custom prompt fixture