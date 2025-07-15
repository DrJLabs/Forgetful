# Modern Testing Practices 2025 - Quick Reference Guide

**Source**: Context7 Documentation + Web Research
**Focus**: Enterprise-grade testing for cloud-deployed background agents
**Updated**: January 27, 2025

---

## 🚀 **KEY 2025 TESTING MODERNIZATIONS**

### **1. Parallel Execution (CRITICAL for Performance)**
```python
# pytest-xdist configuration
addopts = --numprocesses=auto --dist=worksteal

# Expected improvement: 60-70% runtime reduction
# Before: 210s for 377 tests
# After: ~60-80s for 600+ tests
```

### **2. Advanced Async Testing Patterns**
```python
# Modern pytest-asyncio patterns (2025)
import pytest
import asyncio

@pytest.mark.asyncio
async def test_async_context_manager():
    # Correct pattern for connection pools
    pool = await create_connection_pool()
    async with pool.acquire() as conn:
        result = await conn.execute("SELECT 1")
        assert result is not None
```

### **3. Cloud-Native Testing Architecture**
```yaml
# GitHub Actions with Docker-in-Docker support
services:
  docker:
    image: docker:25-dind  # Latest 2025 version
    privileged: true
    env:
      DOCKER_TLS_CERTDIR: /certs

# Self-hosted runners for background agents
runs-on: self-hosted
timeout-minutes: 120  # Extended for background agents
```

---

## 📊 **PERFORMANCE OPTIMIZATION STRATEGIES**

### **Test Runtime Improvements (Based on [pytest-with-eric.com](https://pytest-with-eric.com/pytest-advanced/pytest-improve-runtime/))**

#### **1. Parallel Test Execution**
```bash
# Install dependencies
pip install pytest-xdist pytest-forked

# Run tests in parallel
pytest -n auto --dist=worksteal
pytest -n 4 --dist=each --tx=popen//python=python3.11
```

#### **2. Efficient Fixture Management**
```python
# Session-scoped database fixtures
@pytest.fixture(scope="session")
async def database_session():
    """Single database setup for entire test session"""
    db = await create_test_database()
    yield db
    await cleanup_database(db)

# Function-scoped cleanup only when needed
@pytest.fixture(scope="function")
async def clean_database(database_session):
    """Fast cleanup without full teardown"""
    await database_session.execute("TRUNCATE TABLE test_data")
    yield database_session
```

#### **3. Smart Test Collection**
```python
# Optimize test discovery
addopts =
    --collect-only  # Fast collection analysis
    --co  # Collection only for debugging

# Selective test execution
pytest -m "not slow"  # Skip slow tests in development
pytest -k "not integration"  # Skip integration tests locally
```

#### **4. Database Optimization**
```python
# In-memory databases for unit tests
DATABASE_URL = "sqlite:///:memory:"

# Connection pooling for integration tests
@pytest.fixture(scope="session")
async def db_pool():
    pool = await asyncpg.create_pool(
        DATABASE_URL,
        min_size=1,
        max_size=5,
        command_timeout=60
    )
    yield pool
    await pool.close()
```

---

## 🔧 **TESTCONTAINERS MODERN PATTERNS**

### **Container Orchestration (2025 Best Practices)**
```python
import testcontainers.postgres as tc_postgres
import testcontainers.neo4j as tc_neo4j

class TestEnvironment:
    """Modern testcontainer orchestration"""

    def __init__(self):
        self.postgres = tc_postgres.PostgresContainer("postgres:16")
        self.neo4j = tc_neo4j.Neo4jContainer("neo4j:5.15")

    async def __aenter__(self):
        # Parallel container startup
        await asyncio.gather(
            self.postgres.start(),
            self.neo4j.start()
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Parallel container cleanup
        await asyncio.gather(
            self.postgres.stop(),
            self.neo4j.stop()
        )

# Usage in tests
@pytest.fixture(scope="session")
async def test_environment():
    async with TestEnvironment() as env:
        yield env
```

### **Resource Optimization**
```python
# Container resource limits (prevent CI/CD resource exhaustion)
postgres_container = PostgresContainer("postgres:16").with_kwargs(
    mem_limit="512m",
    cpu_count=1,
    shm_size="128m"
)

# Network optimization
neo4j_container = Neo4jContainer("neo4j:5.15").with_kwargs(
    ports={"7687/tcp": None},  # Random port assignment
    network_mode="bridge"
)
```

---

## ☁️ **CLOUD BACKGROUND AGENT TESTING**

### **GitHub Actions Self-Hosted Runners**
```yaml
# .github/workflows/background-agents.yml
name: Background Agent Testing
on:
  push:
    branches: [main, develop]
  schedule:
    - cron: '0 2 * * *'  # Nightly extended tests

jobs:
  background-agent-tests:
    runs-on: self-hosted  # Extended runtime capability
    timeout-minutes: 120

    strategy:
      matrix:
        agent-type: [memory-agent, search-agent, analytics-agent]
        cloud-env: [aws, gcp, azure]

    steps:
      - name: Setup Docker Environment
        run: |
          docker system prune -f
          docker volume prune -f

      - name: Extended Background Agent Tests
        run: |
          timeout 7200 python -m pytest \
            tests/background_agents/ \
            -m "background_agent" \
            --timeout=3600 \
            -v
```

### **Docker-in-Docker Configuration**
```yaml
# Enhanced DinD for 2025
services:
  docker:
    image: docker:25.0-dind
    privileged: true
    env:
      DOCKER_TLS_CERTDIR: /certs
      DOCKER_DRIVER: overlay2
      DOCKER_STORAGE_DRIVER: overlay2
    volumes:
      - /var/lib/docker
    options: >-
      --security-opt seccomp=unconfined
      --security-opt apparmor=unconfined
      --tmpfs /tmp
      --tmpfs /run
```

---

## 🧪 **ADVANCED TESTING PATTERNS**

### **Property-Based Testing Enhancement**
```python
from hypothesis import given, strategies as st
import hypothesis.extra.asyncio as asyncio_st

@given(
    user_id=st.uuids(),
    memory_content=st.text(min_size=10, max_size=1000),
    metadata=st.dictionaries(
        keys=st.text(min_size=1, max_size=50),
        values=st.one_of(st.text(), st.integers(), st.booleans())
    )
)
@pytest.mark.asyncio
async def test_memory_operations_property_based(user_id, memory_content, metadata):
    """Property-based testing for memory operations"""
    memory = await create_memory(user_id, memory_content, metadata)

    # Properties that should always hold
    assert memory.user_id == user_id
    assert len(memory.content) >= 10
    assert isinstance(memory.metadata, dict)

    # Invariants
    retrieved = await get_memory(memory.id)
    assert retrieved.content == memory.content
```

### **Performance Regression Testing**
```python
import pytest_benchmark

def test_memory_search_performance(benchmark, test_database):
    """Benchmark memory search operations"""

    def search_memories():
        return search_memories_sync("test query", limit=100)

    result = benchmark.pedantic(
        search_memories,
        rounds=10,
        iterations=5,
        warmup_rounds=2
    )

    # Performance assertions
    assert len(result) <= 100
    assert benchmark.stats.stats.mean < 0.5  # Sub-500ms requirement
```

### **Advanced Mock Patterns**
```python
from unittest.mock import AsyncMock, patch
import pytest_mock

@pytest.mark.asyncio
async def test_external_service_integration(mocker):
    """Modern async mocking patterns"""

    # Mock external API calls
    mock_response = AsyncMock()
    mock_response.json.return_value = {"status": "success"}

    with patch('httpx.AsyncClient.post', return_value=mock_response):
        result = await external_service_call("test_data")
        assert result["status"] == "success"

    # Verify mock usage
    mock_response.json.assert_called_once()
```

---

## 📈 **MONITORING & OBSERVABILITY**

### **Test Metrics Collection**
```python
# pytest-benchmark configuration
benchmark_json = "benchmark.json"
benchmark_histogram = True
benchmark_save = "baseline"
benchmark_compare_fail = "min:5%"  # Fail if 5% slower than baseline

# Custom metrics collection
@pytest.fixture(autouse=True)
def track_test_metrics(request):
    """Automatic test performance tracking"""
    start_time = time.time()
    yield
    end_time = time.time()

    # Send metrics to monitoring system
    send_metric(
        "test.duration",
        end_time - start_time,
        tags={
            "test_name": request.node.name,
            "test_type": get_test_type(request)
        }
    )
```

### **CI/CD Integration Metrics**
```yaml
# Enhanced CI/CD monitoring
- name: Collect Test Metrics
  run: |
    python -m pytest \
      --benchmark-json=benchmark.json \
      --junit-xml=test-results.xml \
      --cov-report=xml:coverage.xml

- name: Upload Test Results
  uses: actions/upload-artifact@v4
  with:
    name: test-results
    path: |
      test-results.xml
      coverage.xml
      benchmark.json
```

---

## 🎯 **IMPLEMENTATION PRIORITY**

### **Week 1 (Critical)**
1. **Parallel Execution**: pytest-xdist setup
2. **Async Patterns**: Fix connection pool issues
3. **Database Optimization**: Session-scoped fixtures

### **Week 2 (Performance)**
1. **Benchmark Testing**: pytest-benchmark integration
2. **Container Optimization**: Resource limits and networking
3. **CI/CD Enhancement**: Self-hosted runners

### **Week 3 (Advanced)**
1. **Property-Based Testing**: Hypothesis expansion
2. **Cloud Integration**: Extended runtime testing
3. **Monitoring**: Performance regression detection

---

**Sources**:
- [Context7 pytest documentation](./context7-sources/)
- [Context7 testcontainers documentation](./context7-sources/)
- [Pytest runtime optimization guide](https://pytest-with-eric.com/pytest-advanced/pytest-improve-runtime/)
- [Modern async testing patterns research](./web-search-results/)

**Next Review**: Weekly during implementation
**Status**: ✅ **READY FOR IMPLEMENTATION**
