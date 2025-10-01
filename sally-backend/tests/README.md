# SallyBot Test Suite

This directory contains comprehensive tests for the SallyBot backend application, with special focus on Weaviate and MongoDB storage functionality.

## Test Structure

```
tests/
├── conftest.py                          # Pytest configuration and fixtures
├── test_weaviate_connection.py         # Weaviate connection tests
├── test_mongodb_storage.py             # MongoDB storage tests
├── test_weaviate_mongodb_integration.py # Integration tests
├── test_rag_service.py                  # RAG service tests
└── README.md                            # This file
```

## Test Categories

### Unit Tests
Fast tests with no external dependencies or mocked dependencies.

```bash
pytest -m unit
```

### Integration Tests
Tests that require external services (MongoDB, Weaviate).

```bash
pytest -m integration
```

### Service-Specific Tests

**Weaviate Tests:**
```bash
pytest -m weaviate
```

**MongoDB Tests:**
```bash
pytest -m mongodb
```

**Slow Tests:**
```bash
pytest -m slow
```

## Prerequisites

### Required Services

1. **MongoDB** (for all tests)
   ```bash
   # Docker
   docker run -d -p 27017:27017 --name mongodb mongo:latest
   
   # Or use your existing MongoDB instance
   ```

2. **Weaviate** (for Weaviate and integration tests)
   ```bash
   # Docker Compose (recommended)
   docker-compose up -d
   
   # Or standalone Docker
   docker run -d -p 8080:8080 -p 50051:50051 \
     -e QUERY_DEFAULTS_LIMIT=25 \
     -e AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED=true \
     -e PERSISTENCE_DATA_PATH='/var/lib/weaviate' \
     cr.weaviate.io/semitechnologies/weaviate:latest
   ```

### Environment Variables

Create a `.env.test` file or set these environment variables:

```bash
# MongoDB
DATABASE_URL=mongodb://localhost:27017/SallyChatBot_Test
TEST_DATABASE_URL=mongodb://localhost:27017/SallyChatBot_Test

# Weaviate
WEAVIATE_URL=http://localhost:8080
WEAVIATE_API_KEY=  # Optional for local development

# OpenAI (for vectorization tests)
OPENAI_API_KEY=your_openai_key_here
Embedder_API_KEY=your_embedder_key_here  # Alternative to OPENAI_API_KEY

# Models
RAG_MODEL=gpt-4
CHAT_MODEL=gpt-4
METADATA_MODEL=gpt-4
```

## Running Tests

### Run All Tests
```bash
pytest
```

### Run Specific Test File
```bash
pytest tests/test_weaviate_connection.py
```

### Run Specific Test Class
```bash
pytest tests/test_weaviate_connection.py::TestWeaviateConnection
```

### Run Specific Test Function
```bash
pytest tests/test_weaviate_connection.py::TestWeaviateConnection::test_weaviate_connection_success
```

### Run with Verbose Output
```bash
pytest -v
```

### Run with Coverage
```bash
pytest --cov=app --cov-report=html
```

### Run Tests Excluding Slow Tests
```bash
pytest -m "not slow"
```

### Run Only Integration Tests
```bash
pytest -m integration
```

## Test Coverage

### Weaviate Tests (`test_weaviate_connection.py`)

✅ Connection establishment  
✅ Schema creation  
✅ MarkdownNode storage  
✅ Node deletion  
✅ Vector search  
✅ Cleanup operations  

### MongoDB Tests (`test_mongodb_storage.py`)

✅ Connection and basic operations  
✅ Article CRUD operations  
✅ Article queries with filters  
✅ Search functionality  
✅ Category operations  
✅ Statistics gathering  

### Integration Tests (`test_weaviate_mongodb_integration.py`)

✅ Dual connection setup  
✅ Article sync to Weaviate on publish  
✅ Article update sync  
✅ Article deletion sync  
✅ Draft articles not synced  
✅ Single article migration  
✅ Bulk article migration  
✅ Markdown parsing and tree structure  

### RAG Service Tests (`test_rag_service.py`)

✅ Service factory  
✅ Document retrieval from Weaviate  
✅ MongoDB fallback  
✅ Visibility filtering  
✅ Semantic search quality  
✅ User context handling  

## Common Issues and Solutions

### Issue: "MongoDB not available"
**Solution:** Ensure MongoDB is running on port 27017
```bash
docker ps | grep mongo
```

### Issue: "Weaviate connection failed"
**Solution:** Check Weaviate is running and accessible
```bash
curl http://localhost:8080/v1/.well-known/ready
```

### Issue: "Vectorization not configured"
**Solution:** Set OPENAI_API_KEY or Embedder_API_KEY in environment
```bash
export OPENAI_API_KEY=your_key_here
```

### Issue: Tests fail with "Collection already exists"
**Solution:** Tests should handle this automatically, but you can manually clean:
```bash
# Delete Weaviate data
curl -X DELETE http://localhost:8080/v1/schema/MarkdownNode
```

## Debugging Tests

### Enable Debug Logging
```bash
pytest --log-cli-level=DEBUG
```

### Run Single Test with Print Statements
```bash
pytest -s tests/test_weaviate_connection.py::TestWeaviateConnection::test_weaviate_connection_success
```

### Use Pytest Debugger
```bash
pytest --pdb
```

### Check Test Fixtures
```bash
pytest --fixtures
```

## Writing New Tests

### Example Unit Test
```python
import pytest

@pytest.mark.unit
def test_example():
    assert 1 + 1 == 2
```

### Example Integration Test
```python
import pytest

@pytest.mark.integration
@pytest.mark.weaviate
@pytest.mark.mongodb
@pytest.mark.asyncio
async def test_sync(weaviate_connector_async):
    # Your test code here
    pass
```

### Using Fixtures
```python
@pytest.mark.asyncio
async def test_with_article(test_article, test_admin):
    # test_article and test_admin are automatically created
    assert test_article.author_id == str(test_admin.id)
```

## Continuous Integration

These tests are designed to run in CI/CD pipelines. Make sure your CI environment has:

1. MongoDB service
2. Weaviate service (optional, tests will skip if unavailable)
3. Required environment variables

Example GitHub Actions:
```yaml
services:
  mongodb:
    image: mongo:latest
    ports:
      - 27017:27017
  
  weaviate:
    image: cr.weaviate.io/semitechnologies/weaviate:latest
    ports:
      - 8080:8080
      - 50051:50051
```

## Contributing

When adding new tests:

1. Use appropriate markers (`@pytest.mark.unit`, `@pytest.mark.integration`, etc.)
2. Write descriptive test names and docstrings
3. Clean up test data in fixtures
4. Skip tests gracefully when services unavailable
5. Add new test files to this README

## Performance

- Unit tests: < 1 second each
- Integration tests: 1-5 seconds each
- Slow tests: > 5 seconds (marked with `@pytest.mark.slow`)

Total test suite runtime: ~30-60 seconds (depending on services and data)