# Docker & System Cleanup Guide

## Available Cleanup Scripts

### 1. `./stop_all.sh` - Graceful Stop
**Purpose**: Stop all services while preserving data
- Stops Python processes
- Stops Docker containers  
- Option to remove volumes (prompts user)
- Cleans log files

```bash
./stop_all.sh
```

### 2. `./cleanup_all.sh` - Complete Nuclear Cleanup
**Purpose**: Remove EVERYTHING Docker-related
- Stops all processes
- Removes ALL containers
- Removes ALL volumes (⚠️ DATA LOSS)
- Removes ALL networks
- Optional: Remove ALL images
- Cleans project files

```bash
./cleanup_all.sh
```

## Quick Cleanup Commands

### Remove just TimescaleDB data
```bash
docker-compose down -v
```

### Remove specific volumes
```bash
# List volumes
docker volume ls

# Remove specific volume
docker volume rm VOLUME_NAME
```

### Clean Docker system
```bash
# Remove unused containers, networks, images
docker system prune -a

# Remove everything including volumes
docker system prune -af --volumes
```

### Manual process cleanup
```bash
# Kill specific processes
pkill -f "data_ingestor.py"
pkill -f "platform_monitoring_agent.py"

# Or kill all python processes (careful!)
pkill python3
```

## Disk Space Analysis

### Check Docker disk usage
```bash
docker system df
```

### Check what's using space
```bash
# List all containers (running and stopped)
docker ps -a

# List all volumes
docker volume ls

# List all images
docker images
```

## Recovery After Cleanup

### After partial cleanup (stop_all.sh)
```bash
./start_all.sh  # Data preserved, just restart
```

### After complete cleanup (cleanup_all.sh)
```bash
./start_all.sh  # Fresh start, will recreate everything
```

## Running Interfaces

### Web Dashboard (Streamlit)
```bash
# Use this command to avoid Python environment issues:
python3 -m streamlit run chatbot_interface.py
```

### Interactive CLI
```bash
python3 platform_monitoring_agent.py
```

### REST API
```bash
python3 api_server.py
```

## Cleanup Levels

| Script | Processes | Containers | Volumes | Networks | Images | Data Loss |
|--------|-----------|------------|---------|----------|--------|-----------|
| `stop_all.sh` | ✅ | Optional | Optional | ❌ | ❌ | Optional |
| `cleanup_all.sh` | ✅ | ✅ | ✅ | ✅ | Optional | ⚠️ YES |

## Emergency Cleanup Commands

If scripts don't work, run these manually:

```bash
# Nuclear option - remove everything
docker stop $(docker ps -aq) 2>/dev/null
docker rm $(docker ps -aq) 2>/dev/null  
docker volume rm $(docker volume ls -q) 2>/dev/null
docker network rm $(docker network ls -q) 2>/dev/null
docker system prune -af --volumes

# Kill all Python processes
pkill python3
```

## What Gets Cleaned

### TimescaleDB Data
- All metrics tables
- All anomaly events  
- Continuous aggregates
- Database schema

### Project Files
- `ingestor.log`
- `monitoring_agent.log`
- `test_metrics.db`
- `__pycache__/`
- `*.pyc` files

### Docker Resources
- `timescaledb` container
- Associated volumes
- Custom networks
- Downloaded images (optional)

⚠️ **Important**: Always backup important data before running cleanup scripts!