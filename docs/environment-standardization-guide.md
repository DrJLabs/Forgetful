# Environment Standardization Guide

## Executive Summary
**Objective**: Standardize environment variable management across all mem0-stack services to eliminate deployment complexity and configuration errors.

**Current Problem**: Inconsistent environment variable patterns between mem0 core, OpenMemory API, and OpenMemory UI services leading to deployment issues and configuration drift.

**Timeline**: 3 days
**Risk Level**: Low
**Priority**: High (prerequisite for other stability improvements)

## Current State Analysis

### Service-by-Service Environment Patterns

#### 1. mem0 Core Server (`mem0/server/main.py`)
**Pattern**: Direct `os.environ.get()` with hardcoded defaults
```python
POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "postgres")
POSTGRES_PORT = os.environ.get("POSTGRES_PORT", "5432")
POSTGRES_DB = os.environ.get("POSTGRES_DB", "postgres")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://neo4j:7687")
```
**Issues**:
- No validation
- Hardcoded defaults may not match docker-compose
- No type conversion
- Missing required variable checking

#### 2. OpenMemory API (`openmemory/api/app`)
**Pattern**: Mixed `.env` file loading + os.environ
```python
# database.py
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./openmemory.db")

# config.py
USER_ID = os.getenv("USER", "default_user")
DEFAULT_APP_ID = "openmemory"
```
**Issues**:
- Inconsistent variable naming (`USER` vs `USER_ID`)
- SQLite fallback creates production risks
- Limited validation

#### 3. OpenMemory UI (`openmemory/ui`)
**Pattern**: Next.js environment variables
```env
NEXT_PUBLIC_API_URL=http://localhost:8765
NEXT_PUBLIC_USER_ID=user
```
**Issues**:
- Build-time vs runtime variable confusion
- No validation
- Hardcoded localhost URLs

### docker-compose.yml Environment Variables
**Current Variables Used**:
```yaml
# Inconsistent naming patterns
POSTGRES_USER vs USER
NEO4J_AUTH vs NEO4J_PASSWORD
OPENAI_API_KEY (consistent)
NEXT_PUBLIC_API_URL vs API_URL
```

## Standardization Strategy

### 1. Unified Variable Naming Convention

#### Core Principles
- **Consistent Prefixes**: Service-specific prefixes where needed
- **Descriptive Names**: Clear purpose and scope
- **No Abbreviations**: Full words for clarity
- **Hierarchical Structure**: Group related variables

#### Standard Variable Schema
```bash
# Database Configuration
DATABASE_HOST=postgres-mem0
DATABASE_PORT=5432
DATABASE_NAME=mem0
DATABASE_USER=drj
DATABASE_PASSWORD=secure_password
DATABASE_URL=postgresql://user:pass@host:port/dbname

# Neo4j Configuration
NEO4J_HOST=neo4j-mem0
NEO4J_PORT=7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=secure_password
NEO4J_URL=neo4j://neo4j:secure_password@neo4j-mem0:7687

# OpenAI Configuration
OPENAI_API_KEY=sk-proj-...
OPENAI_MODEL=gpt-4o
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Application Configuration
APP_USER_ID=drj
APP_DEBUG=false
APP_LOG_LEVEL=INFO
APP_ENVIRONMENT=development

# Service URLs
MEM0_API_URL=http://localhost:8000
OPENMEMORY_API_URL=http://localhost:8765
OPENMEMORY_UI_URL=http://localhost:3000

# Frontend Configuration (Next.js)
NEXT_PUBLIC_API_URL=http://localhost:8765
NEXT_PUBLIC_USER_ID=drj
NEXT_PUBLIC_ENVIRONMENT=development
```

### 2. Configuration Management Architecture

#### Centralized Configuration Class
```python
# New file: shared/config.py
from pydantic import BaseSettings, validator
from typing import Optional
import os

class BaseConfig(BaseSettings):
    """Base configuration with common validation patterns"""

    class Config:
        env_file = ".env"
        case_sensitive = True

    @validator('*', pre=True)
    def empty_str_to_none(cls, v):
        if v == '':
            return None
        return v

class DatabaseConfig(BaseConfig):
    """Database configuration with validation"""
    DATABASE_HOST: str = "postgres-mem0"
    DATABASE_PORT: int = 5432
    DATABASE_NAME: str = "mem0"
    DATABASE_USER: str
    DATABASE_PASSWORD: str

    @validator('DATABASE_PASSWORD')
    def validate_password(cls, v):
        if not v or len(v) < 8:
            raise ValueError('Database password must be at least 8 characters')
        return v

    @property
    def database_url(self) -> str:
        return f"postgresql://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"

class Neo4jConfig(BaseConfig):
    """Neo4j configuration with validation"""
    NEO4J_HOST: str = "neo4j-mem0"
    NEO4J_PORT: int = 7687
    NEO4J_USERNAME: str = "neo4j"
    NEO4J_PASSWORD: str

    @property
    def neo4j_url(self) -> str:
        return f"neo4j://{self.NEO4J_USERNAME}:{self.NEO4J_PASSWORD}@{self.NEO4J_HOST}:{self.NEO4J_PORT}"

class OpenAIConfig(BaseConfig):
    """OpenAI configuration with validation"""
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"

    @validator('OPENAI_API_KEY')
    def validate_api_key(cls, v):
        if not v or not v.startswith('sk-'):
            raise ValueError('Invalid OpenAI API key format')
        return v

class AppConfig(BaseConfig):
    """Application configuration"""
    APP_USER_ID: str = "default_user"
    APP_DEBUG: bool = False
    APP_LOG_LEVEL: str = "INFO"
    APP_ENVIRONMENT: str = "development"

    @validator('APP_LOG_LEVEL')
    def validate_log_level(cls, v):
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'Log level must be one of: {valid_levels}')
        return v.upper()

class Config(DatabaseConfig, Neo4jConfig, OpenAIConfig, AppConfig):
    """Combined configuration for all services"""
    pass

# Global config instance
config = Config()
```

## Implementation Plan

### Phase 1: Create Unified Configuration (Day 1)

#### Tasks
1. **Create shared configuration module**
   - `shared/config.py` with Pydantic validation
   - Service-specific config classes
   - Environment variable validation

2. **Create comprehensive .env template**
   - `env.template` with all variables documented
   - Example values and required/optional markings
   - Service-specific sections

3. **Update docker-compose.yml**
   - Standardize variable names
   - Add missing environment variables
   - Document service dependencies

#### Deliverables
- Shared configuration module
- Comprehensive .env template
- Updated docker-compose.yml

### Phase 2: Service Integration (Day 2)

#### mem0 Core Server Updates
```python
# mem0/server/main.py
from shared.config import config

# Replace hardcoded os.environ.get calls
DEFAULT_CONFIG = {
    "version": "v1.1",
    "vector_store": {
        "provider": "pgvector",
        "config": {
            "host": config.DATABASE_HOST,
            "port": config.DATABASE_PORT,
            "dbname": config.DATABASE_NAME,
            "user": config.DATABASE_USER,
            "password": config.DATABASE_PASSWORD,
        },
    },
    "graph_store": {
        "provider": "neo4j",
        "config": {"url": config.neo4j_url},
    },
    "llm": {
        "provider": "openai",
        "config": {
            "api_key": config.OPENAI_API_KEY,
            "model": config.OPENAI_MODEL
        }
    },
}
```

#### OpenMemory API Updates
```python
# openmemory/api/app/database.py
from shared.config import config

DATABASE_URL = config.database_url
engine = create_engine(DATABASE_URL)

# openmemory/api/app/config.py
from shared.config import config

USER_ID = config.APP_USER_ID
DEFAULT_APP_ID = "openmemory"
```

#### OpenMemory UI Updates
```javascript
// openmemory/ui/next.config.js
module.exports = {
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8765',
    NEXT_PUBLIC_USER_ID: process.env.NEXT_PUBLIC_USER_ID || 'default_user',
  },
  // Add runtime configuration validation
}
```

### Phase 3: Validation and Testing (Day 3)

#### Configuration Validation Script
```python
# scripts/validate_config.py
#!/usr/bin/env python3
"""Validate environment configuration before startup"""

import sys
from shared.config import Config

def validate_configuration():
    """Validate all configuration settings"""
    try:
        config = Config()
        print("✅ Configuration validation successful")

        # Test database connection
        print(f"Database URL: {config.database_url}")

        # Test Neo4j connection
        print(f"Neo4j URL: {config.neo4j_url}")

        # Validate OpenAI key format
        print(f"OpenAI API Key: {config.OPENAI_API_KEY[:10]}...")

        return True

    except Exception as e:
        print(f"❌ Configuration validation failed: {e}")
        return False

if __name__ == "__main__":
    if not validate_configuration():
        sys.exit(1)
```

#### Environment Setup Scripts
```bash
#!/bin/bash
# scripts/setup_environment.sh

set -euo pipefail

echo "Setting up mem0-stack environment..."

# Copy template if .env doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env from template..."
    cp env.template .env
    echo "⚠️  Please edit .env with your actual values"
fi

# Validate configuration
echo "Validating configuration..."
python scripts/validate_config.py

# Create service-specific .env files
echo "Creating service-specific environment files..."
envsubst < env.template > openmemory/api/.env
envsubst < env.template > openmemory/ui/.env

echo "✅ Environment setup complete"
```

## Unified Environment Template

### Complete .env Template
```bash
# env.template
# mem0-stack Environment Configuration
# Copy to .env and customize for your environment

#===========================================
# Database Configuration (PostgreSQL)
#===========================================
DATABASE_HOST=postgres-mem0
DATABASE_PORT=5432
DATABASE_NAME=mem0
DATABASE_USER=drj
DATABASE_PASSWORD=your_secure_password_here

# Derived variable (auto-generated)
# DATABASE_URL=postgresql://${DATABASE_USER}:${DATABASE_PASSWORD}@${DATABASE_HOST}:${DATABASE_PORT}/${DATABASE_NAME}

#===========================================
# Graph Database Configuration (Neo4j)
#===========================================
NEO4J_HOST=neo4j-mem0
NEO4J_PORT=7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_neo4j_password_here

# Legacy format for backward compatibility
NEO4J_AUTH=neo4j/${NEO4J_PASSWORD}
NEO4J_URI=bolt://${NEO4J_HOST}:${NEO4J_PORT}

#===========================================
# OpenAI Configuration
#===========================================
OPENAI_API_KEY=sk-proj-your-api-key-here
OPENAI_MODEL=gpt-4o
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

#===========================================
# Application Configuration
#===========================================
APP_USER_ID=your_username_here
APP_DEBUG=false
APP_LOG_LEVEL=INFO
APP_ENVIRONMENT=development

#===========================================
# Service URLs
#===========================================
MEM0_API_URL=http://localhost:8000
OPENMEMORY_API_URL=http://localhost:8765
OPENMEMORY_UI_URL=http://localhost:3000

#===========================================
# Frontend Configuration (Next.js)
#===========================================
NEXT_PUBLIC_API_URL=http://localhost:8765
NEXT_PUBLIC_USER_ID=${APP_USER_ID}
NEXT_PUBLIC_ENVIRONMENT=${APP_ENVIRONMENT}

#===========================================
# Docker Compose Variables
#===========================================
COMPOSE_PROJECT_NAME=mem0-stack
POSTGRES_USER=${DATABASE_USER}
POSTGRES_PASSWORD=${DATABASE_PASSWORD}
POSTGRES_DB=${DATABASE_NAME}

# Legacy compatibility
USER=${APP_USER_ID}
API_KEY=optional_api_key_if_needed
```

## Testing Strategy

### Configuration Testing
```python
# tests/test_configuration.py
import pytest
from shared.config import Config
import os

def test_database_config_validation():
    """Test database configuration validation"""
    # Test valid config
    os.environ.update({
        'DATABASE_USER': 'testuser',
        'DATABASE_PASSWORD': 'testpass123'
    })
    config = Config()
    assert config.DATABASE_USER == 'testuser'

    # Test invalid password
    os.environ['DATABASE_PASSWORD'] = 'short'
    with pytest.raises(ValueError):
        Config()

def test_openai_config_validation():
    """Test OpenAI configuration validation"""
    os.environ['OPENAI_API_KEY'] = 'sk-test123'
    config = Config()
    assert config.OPENAI_API_KEY == 'sk-test123'

    # Test invalid API key
    os.environ['OPENAI_API_KEY'] = 'invalid-key'
    with pytest.raises(ValueError):
        Config()

def test_environment_variable_precedence():
    """Test that environment variables override defaults"""
    os.environ['DATABASE_HOST'] = 'custom-host'
    config = Config()
    assert config.DATABASE_HOST == 'custom-host'
```

### Integration Testing
```bash
#!/bin/bash
# tests/test_environment_integration.sh

# Test environment setup
echo "Testing environment setup..."
./scripts/setup_environment.sh

# Test configuration validation
echo "Testing configuration validation..."
python scripts/validate_config.py

# Test service startup with new configuration
echo "Testing service startup..."
docker-compose config  # Validate docker-compose
docker-compose up -d postgres neo4j
sleep 10

# Test database connectivity
echo "Testing database connectivity..."
docker-compose exec postgres psql -U $DATABASE_USER -d $DATABASE_NAME -c "SELECT 1;"

# Test Neo4j connectivity
echo "Testing Neo4j connectivity..."
docker-compose exec neo4j cypher-shell -u $NEO4J_USERNAME -p $NEO4J_PASSWORD "RETURN 1;"

echo "✅ Environment integration tests complete"
```

## Migration Strategy

### Backward Compatibility
- **Phase 1**: Add new configuration alongside existing
- **Phase 2**: Update services to use new configuration
- **Phase 3**: Remove old configuration patterns
- **Phase 4**: Clean up deprecated variables

### Rollback Plan
1. Keep existing environment patterns during transition
2. Feature flag for new configuration system
3. Quick rollback script to restore old patterns
4. Validation that both systems work in parallel

## Success Metrics

### Configuration Consistency
- [ ] All services use identical variable names
- [ ] Zero hardcoded defaults in service code
- [ ] 100% environment variable validation coverage

### Operational Improvement
- [ ] Deployment setup time reduced by 50%
- [ ] Zero configuration-related startup failures
- [ ] Complete documentation of all variables

### Developer Experience
- [ ] Single .env file for all services
- [ ] Clear error messages for configuration issues
- [ ] Automated configuration validation

## Maintenance

### Documentation Updates
1. **README.md**: Update setup instructions
2. **Environment Variables Guide**: Complete reference
3. **Troubleshooting Guide**: Configuration-related issues
4. **Deployment Guide**: Production configuration patterns

### Ongoing Validation
- Pre-commit hooks for configuration validation
- CI/CD pipeline configuration testing
- Regular configuration audit scripts
- Production configuration monitoring

---

## Quick Start Commands

```bash
# Day 1: Create unified configuration
./scripts/create_shared_config.sh

# Day 2: Update services
./scripts/update_service_configs.sh

# Day 3: Validate and test
./scripts/validate_and_test.sh

# Deploy standardized configuration
./scripts/deploy_config_changes.sh
```

**Expected Outcome**: Unified, validated, and maintainable environment configuration across all mem0-stack services with zero deployment configuration issues.
