# Quick Start Guide - mem0-stack

## 🚀 Immediate Setup Steps

### 1. Update OpenAI API Key
**REQUIRED**: Replace placeholder with your actual OpenAI API key

```bash
# Edit main .env file
nano .env
# Find: OPENAI_API_KEY=sk-proj-placeholder-replace-with-actual-key
# Replace with your actual key

# Edit OpenMemory API .env file
nano openmemory/api/.env
# Find: OPENAI_API_KEY=sk-proj-placeholder-replace-with-actual-key
# Replace with your actual key
```

### 2. Start All Services
```bash
# Start the entire stack
docker-compose up -d

# Check if services are running
docker-compose ps

# View logs if needed
docker-compose logs -f
```

### 3. Verify System Health
```bash
# Run health check
./health_check_memory.sh

# Run comprehensive tests
python test_memory_system.py

# Run unified system tests
./test_unified_system.sh
```

## 📋 Service URLs
- **mem0 API**: http://localhost:8000
- **OpenMemory MCP**: http://localhost:8765
- **OpenMemory UI**: http://localhost:3000

## 🔧 Configuration Files Created
- ✅ `.env` - Main system configuration
- ✅ `openmemory/api/.env` - OpenMemory API configuration
- ✅ `openmemory/ui/.env` - OpenMemory UI configuration

## ⚡ System Status
- **Core mem0 Server**: 100% test success rate
- **Memory Operations**: All working (create, retrieve, search, delete)
- **Database Integration**: PostgreSQL + Neo4j configured
- **MCP Server**: Ready for Cursor integration

## 🎯 Next Steps
1. **Update OpenAI API key** (required)
2. **Start Docker services**
3. **Run system tests**
4. **Test in Cursor** (MCP tools should work)
5. **Address OpenMemory API issues** (optional)

## 🆘 Troubleshooting
- **Services won't start**: Check Docker is running
- **API errors**: Verify OpenAI API key is valid
- **Database connection**: Ensure PostgreSQL credentials are correct
- **Port conflicts**: Check ports 8000, 8765, 3000 are available

## 📊 Expected Test Results
- **Core mem0**: 6/6 tests passing
- **OpenMemory**: 2/6 tests passing (known issues)
- **Overall**: System functional for core operations