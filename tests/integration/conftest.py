"""
Pytest configuration for AI Companion Platform tests
"""
import pytest
import sys
import os

# Add repo root to path (go up from tests/integration/ to repo root)
_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, _repo_root)

# Some services use bare imports (e.g. "from config import get_settings")
# that require their own directory on sys.path.
_llm_dir = os.path.join(_repo_root, 'src', 'services', 'llm')
if _llm_dir not in sys.path:
    sys.path.insert(0, _llm_dir)


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for async tests"""
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def mock_mongodb():
    """Mock MongoDB connection"""
    from unittest.mock import AsyncMock, patch
    
    with patch('shared.database.mongodb.get_mongodb') as mock:
        db = AsyncMock()
        mock.return_value = db
        yield db


@pytest.fixture
async def mock_redis():
    """Mock Redis connection"""
    from unittest.mock import AsyncMock, patch
    
    with patch('shared.database.redis.get_redis') as mock:
        client = AsyncMock()
        mock.return_value = client
        yield client
