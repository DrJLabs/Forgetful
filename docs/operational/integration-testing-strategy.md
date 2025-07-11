# mem0-Stack Integration Testing Strategy

## Overview

This document defines the comprehensive integration testing strategy for the mem0-stack optimization project. The strategy ensures all optimizations maintain system integrity and autonomous AI operations continue functioning correctly.

## Testing Scope

### Systems Under Test
- **mem0 API Service** (localhost:8000)
- **OpenMemory MCP Server** (localhost:8765)
- **OpenMemory UI** (localhost:3000)
- **PostgreSQL Database** (vector storage)
- **Neo4j Database** (graph relationships)
- **Cursor IDE Integration** (via MCP protocol)

### Integration Points
- **mem0 ↔ PostgreSQL**: Vector storage and retrieval
- **mem0 ↔ Neo4j**: Graph relationship management
- **mem0 ↔ OpenAI**: Embedding generation and LLM operations
- **MCP Server ↔ PostgreSQL**: Memory operations via MCP protocol
- **MCP Server ↔ Neo4j**: Graph operations via MCP protocol
- **Cursor IDE ↔ MCP Server**: Autonomous AI agent operations
- **UI ↔ MCP Server**: Web interface operations
- **All Services ↔ Docker Network**: Service discovery and communication

## Test Categories

### 1. Service Integration Tests

#### 1.1 mem0 API Integration Tests

**Test Suite**: `test_mem0_integration.py`

```python
import pytest
import requests
import json
from typing import Dict, Any

class TestMem0Integration:
    
    def test_mem0_health_check(self):
        """Test mem0 API health endpoint"""
        response = requests.get("http://localhost:8000/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
    
    def test_mem0_database_connectivity(self):
        """Test mem0 can connect to databases"""
        # Test memory creation (requires both PostgreSQL and Neo4j)
        payload = {
            "messages": [{"role": "user", "content": "integration test"}],
            "user_id": "test_user"
        }
        response = requests.post("http://localhost:8000/memories", json=payload)
        assert response.status_code == 200
        
        # Test memory retrieval
        response = requests.get("http://localhost:8000/memories?user_id=test_user")
        assert response.status_code == 200
        assert len(response.json()) > 0
    
    def test_mem0_search_functionality(self):
        """Test mem0 search operations"""
        # Create test memory
        self.test_mem0_database_connectivity()
        
        # Search for memory
        payload = {"query": "integration test", "user_id": "test_user"}
        response = requests.post("http://localhost:8000/search", json=payload)
        assert response.status_code == 200
        assert len(response.json()) > 0
    
    def test_mem0_performance_baseline(self):
        """Test mem0 response times meet baseline requirements"""
        import time
        
        # Test memory creation performance
        start_time = time.time()
        payload = {
            "messages": [{"role": "user", "content": "performance test"}],
            "user_id": "perf_test"
        }
        response = requests.post("http://localhost:8000/memories", json=payload)
        end_time = time.time()
        
        assert response.status_code == 200
        assert (end_time - start_time) < 2.0  # 2 second threshold
        
        # Test search performance
        start_time = time.time()
        payload = {"query": "performance", "user_id": "perf_test"}
        response = requests.post("http://localhost:8000/search", json=payload)
        end_time = time.time()
        
        assert response.status_code == 200
        assert (end_time - start_time) < 1.0  # 1 second threshold
```

#### 1.2 MCP Server Integration Tests

**Test Suite**: `test_mcp_integration.py`

```python
import pytest
import requests
import json
import asyncio
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters

class TestMCPIntegration:
    
    def test_mcp_server_health(self):
        """Test MCP server health and availability"""
        response = requests.get("http://localhost:8765/docs")
        assert response.status_code == 200
    
    def test_mcp_memory_operations(self):
        """Test MCP memory operations"""
        # Test memory creation via MCP
        payload = {
            "messages": [{"role": "user", "content": "MCP integration test"}],
            "user_id": "mcp_test"
        }
        response = requests.post("http://localhost:8765/memories", json=payload)
        assert response.status_code == 200
        
        # Test memory retrieval via MCP
        response = requests.get("http://localhost:8765/memories?user_id=mcp_test")
        assert response.status_code == 200
    
    def test_mcp_search_operations(self):
        """Test MCP search operations"""
        # Create test memory
        self.test_mcp_memory_operations()
        
        # Search via MCP
        payload = {"query": "MCP integration", "user_id": "mcp_test"}
        response = requests.post("http://localhost:8765/search", json=payload)
        assert response.status_code == 200
    
    async def test_mcp_protocol_compliance(self):
        """Test MCP protocol compliance"""
        # This would test the actual MCP protocol communication
        # Implementation depends on MCP client library
        pass
```

### 2. Database Integration Tests

#### 2.1 PostgreSQL Integration Tests

**Test Suite**: `test_postgres_integration.py`

```python
import pytest
import psycopg2
import os
from contextlib import contextmanager

class TestPostgreSQLIntegration:
    
    @contextmanager
    def get_db_connection(self):
        """Get database connection for testing"""
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            database="mem0",
            user=os.getenv("POSTGRES_USER", "drj"),
            password=os.getenv("POSTGRES_PASSWORD")
        )
        try:
            yield conn
        finally:
            conn.close()
    
    def test_postgres_connectivity(self):
        """Test PostgreSQL database connectivity"""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            assert result[0] == 1
    
    def test_postgres_extensions(self):
        """Test required PostgreSQL extensions"""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM pg_extension WHERE extname = 'vector'")
            result = cursor.fetchone()
            assert result is not None, "pgvector extension not installed"
    
    def test_postgres_memory_table(self):
        """Test memory table operations"""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Test table exists
            cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'memories'")
            result = cursor.fetchone()
            assert result[0] > 0, "memories table not found"
            
            # Test basic operations
            cursor.execute("SELECT COUNT(*) FROM memories")
            result = cursor.fetchone()
            assert result[0] >= 0  # Should not fail
    
    def test_postgres_vector_operations(self):
        """Test vector operations"""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Test vector similarity search
            cursor.execute("SELECT COUNT(*) FROM memories WHERE embedding IS NOT NULL")
            result = cursor.fetchone()
            # Should not fail, even if no vectors exist
            assert result[0] >= 0
    
    def test_postgres_performance(self):
        """Test PostgreSQL performance"""
        import time
        
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Test query performance
            start_time = time.time()
            cursor.execute("SELECT COUNT(*) FROM memories")
            cursor.fetchone()
            end_time = time.time()
            
            assert (end_time - start_time) < 0.1  # 100ms threshold
```

#### 2.2 Neo4j Integration Tests

**Test Suite**: `test_neo4j_integration.py`

```python
import pytest
from neo4j import GraphDatabase
import os

class TestNeo4jIntegration:
    
    def get_neo4j_driver(self):
        """Get Neo4j driver for testing"""
        return GraphDatabase.driver(
            "bolt://localhost:7687",
            auth=("neo4j", os.getenv("NEO4J_PASSWORD", "data2f!re"))
        )
    
    def test_neo4j_connectivity(self):
        """Test Neo4j database connectivity"""
        with self.get_neo4j_driver() as driver:
            with driver.session() as session:
                result = session.run("RETURN 1 as test")
                record = result.single()
                assert record["test"] == 1
    
    def test_neo4j_memory_nodes(self):
        """Test memory node operations"""
        with self.get_neo4j_driver() as driver:
            with driver.session() as session:
                # Test node creation/retrieval
                result = session.run("MATCH (n:Memory) RETURN count(n) as count")
                record = result.single()
                assert record["count"] >= 0
    
    def test_neo4j_relationship_operations(self):
        """Test relationship operations"""
        with self.get_neo4j_driver() as driver:
            with driver.session() as session:
                # Test relationship queries
                result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
                record = result.single()
                assert record["count"] >= 0
    
    def test_neo4j_performance(self):
        """Test Neo4j performance"""
        import time
        
        with self.get_neo4j_driver() as driver:
            with driver.session() as session:
                start_time = time.time()
                session.run("MATCH (n:Memory) RETURN count(n)")
                end_time = time.time()
                
                assert (end_time - start_time) < 0.1  # 100ms threshold
```

### 3. End-to-End Integration Tests

#### 3.1 Autonomous AI Workflow Tests

**Test Suite**: `test_autonomous_workflow.py`

```python
import pytest
import requests
import json
import time

class TestAutonomousWorkflow:
    
    def test_complete_memory_workflow(self):
        """Test complete memory workflow from creation to retrieval"""
        user_id = "workflow_test"
        
        # Step 1: Create memory
        payload = {
            "messages": [
                {"role": "user", "content": "I need to remember this important information"},
                {"role": "assistant", "content": "I'll help you remember that"}
            ],
            "user_id": user_id
        }
        
        response = requests.post("http://localhost:8000/memories", json=payload)
        assert response.status_code == 200
        memory_data = response.json()
        
        # Step 2: Search for memory
        search_payload = {"query": "important information", "user_id": user_id}
        response = requests.post("http://localhost:8000/search", json=search_payload)
        assert response.status_code == 200
        search_results = response.json()
        assert len(search_results) > 0
        
        # Step 3: Retrieve specific memory
        response = requests.get(f"http://localhost:8000/memories?user_id={user_id}")
        assert response.status_code == 200
        memories = response.json()
        assert len(memories) > 0
        
        # Step 4: Update memory
        memory_id = memories[0]['id']
        update_payload = {"text": "Updated important information"}
        response = requests.put(f"http://localhost:8000/memories/{memory_id}", json=update_payload)
        assert response.status_code == 200
        
        # Step 5: Verify update
        response = requests.get(f"http://localhost:8000/memories/{memory_id}")
        assert response.status_code == 200
    
    def test_mcp_autonomous_operations(self):
        """Test MCP autonomous operations"""
        user_id = "mcp_autonomous_test"
        
        # Test autonomous memory creation via MCP
        payload = {
            "messages": [{"role": "user", "content": "Autonomous AI memory test"}],
            "user_id": user_id
        }
        
        response = requests.post("http://localhost:8765/memories", json=payload)
        assert response.status_code == 200
        
        # Test autonomous search via MCP
        search_payload = {"query": "autonomous AI", "user_id": user_id}
        response = requests.post("http://localhost:8765/search", json=search_payload)
        assert response.status_code == 200
        
        # Test autonomous retrieval via MCP
        response = requests.get(f"http://localhost:8765/memories?user_id={user_id}")
        assert response.status_code == 200
    
    def test_cursor_integration_workflow(self):
        """Test Cursor IDE integration workflow"""
        # This test would simulate Cursor IDE operations
        # Implementation depends on Cursor MCP client setup
        pass
```

#### 3.2 Performance Integration Tests

**Test Suite**: `test_performance_integration.py`

```python
import pytest
import requests
import time
import concurrent.futures
from typing import List

class TestPerformanceIntegration:
    
    def test_concurrent_memory_operations(self):
        """Test concurrent memory operations"""
        def create_memory(user_id: str) -> bool:
            payload = {
                "messages": [{"role": "user", "content": f"Concurrent test {user_id}"}],
                "user_id": user_id
            }
            response = requests.post("http://localhost:8000/memories", json=payload)
            return response.status_code == 200
        
        # Test with 10 concurrent operations
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(create_memory, f"user_{i}") for i in range(10)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        assert all(results), "Some concurrent operations failed"
    
    def test_load_testing_memory_creation(self):
        """Test load on memory creation"""
        start_time = time.time()
        success_count = 0
        
        for i in range(50):
            payload = {
                "messages": [{"role": "user", "content": f"Load test {i}"}],
                "user_id": f"load_test_{i}"
            }
            response = requests.post("http://localhost:8000/memories", json=payload)
            if response.status_code == 200:
                success_count += 1
        
        end_time = time.time()
        duration = end_time - start_time
        
        assert success_count >= 45  # 90% success rate
        assert duration < 30  # Complete in under 30 seconds
    
    def test_search_performance_load(self):
        """Test search performance under load"""
        # Create test data
        for i in range(10):
            payload = {
                "messages": [{"role": "user", "content": f"Search test data {i}"}],
                "user_id": "search_test"
            }
            requests.post("http://localhost:8000/memories", json=payload)
        
        # Test search performance
        start_time = time.time()
        for i in range(20):
            payload = {"query": "search test", "user_id": "search_test"}
            response = requests.post("http://localhost:8000/search", json=payload)
            assert response.status_code == 200
        
        end_time = time.time()
        duration = end_time - start_time
        
        assert duration < 10  # 20 searches in under 10 seconds
```

### 4. Regression Testing

#### 4.1 Optimization Regression Tests

**Test Suite**: `test_optimization_regression.py`

```python
import pytest
import requests
import json
import os

class TestOptimizationRegression:
    
    def test_epic1_performance_regression(self):
        """Test Epic 1 performance optimizations don't break functionality"""
        # Test caching layer
        user_id = "epic1_test"
        
        # Create memory
        payload = {
            "messages": [{"role": "user", "content": "Epic 1 test"}],
            "user_id": user_id
        }
        response = requests.post("http://localhost:8000/memories", json=payload)
        assert response.status_code == 200
        
        # Test cached retrieval
        response = requests.get(f"http://localhost:8000/memories?user_id={user_id}")
        assert response.status_code == 200
        
        # Test search with caching
        search_payload = {"query": "Epic 1", "user_id": user_id}
        response = requests.post("http://localhost:8000/search", json=search_payload)
        assert response.status_code == 200
    
    def test_epic2_intelligence_regression(self):
        """Test Epic 2 intelligence optimizations don't break functionality"""
        user_id = "epic2_test"
        
        # Test intelligent memory storage
        payload = {
            "messages": [{"role": "user", "content": "Epic 2 intelligence test"}],
            "user_id": user_id
        }
        response = requests.post("http://localhost:8000/memories", json=payload)
        assert response.status_code == 200
        
        # Test context-aware retrieval
        search_payload = {"query": "intelligence", "user_id": user_id}
        response = requests.post("http://localhost:8000/search", json=search_payload)
        assert response.status_code == 200
    
    def test_epic3_mcp_regression(self):
        """Test Epic 3 MCP optimizations don't break functionality"""
        user_id = "epic3_test"
        
        # Test MCP operations
        payload = {
            "messages": [{"role": "user", "content": "Epic 3 MCP test"}],
            "user_id": user_id
        }
        response = requests.post("http://localhost:8765/memories", json=payload)
        assert response.status_code == 200
        
        # Test MCP search
        search_payload = {"query": "MCP", "user_id": user_id}
        response = requests.post("http://localhost:8765/search", json=search_payload)
        assert response.status_code == 200
    
    def test_epic4_monitoring_regression(self):
        """Test Epic 4 monitoring doesn't impact functionality"""
        # Test that monitoring doesn't slow down operations
        import time
        
        start_time = time.time()
        payload = {
            "messages": [{"role": "user", "content": "Epic 4 monitoring test"}],
            "user_id": "epic4_test"
        }
        response = requests.post("http://localhost:8000/memories", json=payload)
        end_time = time.time()
        
        assert response.status_code == 200
        assert (end_time - start_time) < 2.0  # Not significantly slower
```

### 5. Failure Testing

#### 5.1 Fault Tolerance Tests

**Test Suite**: `test_fault_tolerance.py`

```python
import pytest
import requests
import docker
import time

class TestFaultTolerance:
    
    def setup_class(self):
        """Setup Docker client for container management"""
        self.client = docker.from_env()
    
    def test_postgres_failure_recovery(self):
        """Test system behavior when PostgreSQL fails"""
        # Stop PostgreSQL
        postgres_container = self.client.containers.get("postgres-mem0")
        postgres_container.stop()
        
        # Test graceful degradation
        payload = {
            "messages": [{"role": "user", "content": "DB failure test"}],
            "user_id": "db_test"
        }
        response = requests.post("http://localhost:8000/memories", json=payload)
        # Should either succeed (cached) or fail gracefully
        assert response.status_code in [200, 500, 503]
        
        # Restart PostgreSQL
        postgres_container.start()
        time.sleep(10)  # Wait for startup
        
        # Test recovery
        response = requests.post("http://localhost:8000/memories", json=payload)
        assert response.status_code == 200
    
    def test_neo4j_failure_recovery(self):
        """Test system behavior when Neo4j fails"""
        # Stop Neo4j
        neo4j_container = self.client.containers.get("neo4j-mem0")
        neo4j_container.stop()
        
        # Test graceful degradation
        payload = {
            "messages": [{"role": "user", "content": "Neo4j failure test"}],
            "user_id": "neo4j_test"
        }
        response = requests.post("http://localhost:8000/memories", json=payload)
        # Should either succeed (degraded) or fail gracefully
        assert response.status_code in [200, 500, 503]
        
        # Restart Neo4j
        neo4j_container.start()
        time.sleep(20)  # Wait for startup
        
        # Test recovery
        response = requests.post("http://localhost:8000/memories", json=payload)
        assert response.status_code == 200
    
    def test_mcp_server_failure_recovery(self):
        """Test MCP server failure and recovery"""
        # Stop MCP server
        mcp_container = self.client.containers.get("openmemory-mcp")
        mcp_container.stop()
        
        # Test failure detection
        response = requests.get("http://localhost:8765/docs")
        assert response.status_code != 200
        
        # Restart MCP server
        mcp_container.start()
        time.sleep(5)  # Wait for startup
        
        # Test recovery
        response = requests.get("http://localhost:8765/docs")
        assert response.status_code == 200
```

## Test Execution Strategy

### 1. Test Environment Setup

**Prerequisites**:
```bash
# Install test dependencies
pip install pytest requests psycopg2-binary neo4j docker

# Set environment variables
export POSTGRES_USER=drj
export POSTGRES_PASSWORD=your_password
export NEO4J_PASSWORD=data2f!re
export OPENAI_API_KEY=your_key
```

**Test Data Setup**:
```bash
# Create test data
python scripts/create_test_data.py

# Backup current data
./scripts/backup_before_testing.sh
```

### 2. Test Execution Order

**Phase 1: Service Integration Tests**
```bash
pytest tests/integration/test_mem0_integration.py -v
pytest tests/integration/test_mcp_integration.py -v
pytest tests/integration/test_postgres_integration.py -v
pytest tests/integration/test_neo4j_integration.py -v
```

**Phase 2: End-to-End Tests**
```bash
pytest tests/integration/test_autonomous_workflow.py -v
pytest tests/integration/test_performance_integration.py -v
```

**Phase 3: Regression Tests**
```bash
pytest tests/integration/test_optimization_regression.py -v
```

**Phase 4: Failure Tests**
```bash
pytest tests/integration/test_fault_tolerance.py -v
```

### 3. Continuous Integration

**CI Pipeline Integration**:
```yaml
# .github/workflows/integration-tests.yml
name: Integration Tests

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  integration-tests:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.9
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest requests psycopg2-binary neo4j docker
    
    - name: Start services
      run: |
        docker-compose up -d
        sleep 30
    
    - name: Run integration tests
      run: |
        pytest tests/integration/ -v --tb=short
    
    - name: Cleanup
      if: always()
      run: |
        docker-compose down -v
```

## Test Reporting and Analysis

### 1. Test Metrics Collection

**Test Results Dashboard**:
```python
# test_metrics.py
import json
import time
from datetime import datetime

class TestMetrics:
    def __init__(self):
        self.metrics = {
            "timestamp": datetime.now().isoformat(),
            "test_results": {},
            "performance_metrics": {},
            "failure_analysis": {}
        }
    
    def record_test_result(self, test_name: str, result: str, duration: float):
        self.metrics["test_results"][test_name] = {
            "result": result,
            "duration": duration
        }
    
    def record_performance_metric(self, metric_name: str, value: float):
        self.metrics["performance_metrics"][metric_name] = value
    
    def save_metrics(self, filename: str):
        with open(filename, 'w') as f:
            json.dump(self.metrics, f, indent=2)
```

### 2. Performance Regression Detection

**Baseline Comparison**:
```python
# performance_regression.py
import json
from typing import Dict, List

class PerformanceRegression:
    def __init__(self, baseline_file: str):
        with open(baseline_file, 'r') as f:
            self.baseline = json.load(f)
    
    def check_regression(self, current_metrics: Dict) -> List[str]:
        regressions = []
        
        for metric, current_value in current_metrics.items():
            if metric in self.baseline:
                baseline_value = self.baseline[metric]
                # 20% regression threshold
                if current_value > baseline_value * 1.2:
                    regressions.append(f"{metric}: {current_value:.3f} vs {baseline_value:.3f} (baseline)")
        
        return regressions
```

### 3. Test Result Analysis

**Failure Pattern Detection**:
```python
# failure_analysis.py
import re
from collections import Counter
from typing import List, Dict

class FailureAnalysis:
    def __init__(self):
        self.failure_patterns = {
            "connection_timeout": r"timeout|connection.*failed",
            "database_error": r"database.*error|sql.*error",
            "memory_error": r"out of memory|memory.*error",
            "performance_degradation": r"slow|timeout|performance"
        }
    
    def analyze_failures(self, test_logs: List[str]) -> Dict[str, int]:
        pattern_counts = Counter()
        
        for log in test_logs:
            for pattern_name, pattern in self.failure_patterns.items():
                if re.search(pattern, log, re.IGNORECASE):
                    pattern_counts[pattern_name] += 1
        
        return dict(pattern_counts)
```

## Maintenance and Updates

### 1. Test Maintenance Schedule

**Weekly Tasks**:
- Review test results and update baselines
- Add new tests for new features
- Update test data and cleanup

**Monthly Tasks**:
- Performance baseline updates
- Test environment maintenance
- Test suite optimization

### 2. Test Suite Evolution

**Adding New Tests**:
```python
# Template for new integration tests
class TestNewFeature:
    def setup_class(self):
        """Setup test environment"""
        pass
    
    def test_new_feature_integration(self):
        """Test new feature integration"""
        pass
    
    def test_new_feature_performance(self):
        """Test new feature performance"""
        pass
    
    def test_new_feature_regression(self):
        """Test new feature doesn't break existing functionality"""
        pass
```

## Success Criteria

### 1. Test Coverage Requirements

- **Service Integration**: 100% of service endpoints tested
- **Database Integration**: 100% of database operations tested
- **End-to-End Workflows**: 100% of autonomous workflows tested
- **Performance Baselines**: All performance targets validated
- **Regression Coverage**: All optimization epics tested

### 2. Performance Thresholds

- **Response Time**: < 100ms for memory operations
- **Throughput**: > 100 operations/second
- **Error Rate**: < 1% under normal load
- **Recovery Time**: < 30 seconds after failure

### 3. Quality Gates

- **All integration tests pass**: 100% pass rate required
- **Performance regression**: < 20% degradation acceptable
- **Fault tolerance**: System recovers from single service failures
- **Data integrity**: No data corruption under any test scenario

---

**Document Version**: 1.0  
**Last Updated**: January 11, 2025  
**Next Review**: February 11, 2025  
**Owner**: Winston (Architect)  
**Approval**: Pending PO Review 