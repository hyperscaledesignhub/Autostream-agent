#!/bin/bash

# Complete Cleanup Script
# Removes all Docker containers, volumes, networks, and project files

echo "🧹 Complete System Cleanup"
echo "=========================="
echo "⚠️  WARNING: This will remove ALL Docker containers, volumes, and networks!"
echo "This includes data from TimescaleDB and any other Docker resources."
echo ""

# Ask for confirmation
read -p "Are you sure you want to continue? (type 'yes' to confirm): " confirmation

if [ "$confirmation" != "yes" ]; then
    echo "❌ Cleanup cancelled"
    exit 0
fi

echo ""
echo "🛑 Starting complete cleanup..."

# 1. Stop all processes first
echo "📡 Stopping all Python services..."
pkill -f "data_ingestor.py" 2>/dev/null || true
pkill -f "platform_monitoring_agent.py" 2>/dev/null || true
pkill -f "api_server.py" 2>/dev/null || true
pkill -f "chatbot_interface.py" 2>/dev/null || true
pkill -f "simple_monitoring_agent.py" 2>/dev/null || true
echo "✅ Python services stopped"

# 2. Stop and remove Docker containers
echo "🐳 Stopping and removing Docker containers..."

# Stop TimescaleDB container specifically  
docker stop timescaledb 2>/dev/null || true
docker rm timescaledb 2>/dev/null || true
echo "✅ TimescaleDB container stopped and removed"

# Stop all running containers
RUNNING_CONTAINERS=$(docker ps -q)
if [ ! -z "$RUNNING_CONTAINERS" ]; then
    docker stop $RUNNING_CONTAINERS 2>/dev/null || true
    echo "✅ All running containers stopped"
else
    echo "✅ No running containers found"
fi

# Remove all containers (running and stopped)
ALL_CONTAINERS=$(docker ps -aq)
if [ ! -z "$ALL_CONTAINERS" ]; then
    docker rm -f $ALL_CONTAINERS 2>/dev/null || true
    echo "✅ All containers removed"
else
    echo "✅ No containers to remove"
fi

# 3. Remove Docker volumes
echo "💾 Removing Docker volumes..."
ALL_VOLUMES=$(docker volume ls -q)
if [ ! -z "$ALL_VOLUMES" ]; then
    docker volume rm $ALL_VOLUMES 2>/dev/null || true
    echo "✅ All Docker volumes removed"
else
    echo "✅ No Docker volumes to remove"
fi

# 4. Remove Docker networks (except default ones)
echo "🌐 Removing Docker networks..."
CUSTOM_NETWORKS=$(docker network ls --filter type=custom -q)
if [ ! -z "$CUSTOM_NETWORKS" ]; then
    docker network rm $CUSTOM_NETWORKS 2>/dev/null || true
    echo "✅ Custom Docker networks removed"
else
    echo "✅ No custom networks to remove"
fi

# 5. Remove Docker images (optional - uncomment if you want to remove images too)
echo "🖼️  Docker images cleanup..."
read -p "Remove all Docker images as well? (y/N): " remove_images
if [[ "$remove_images" =~ ^[Yy]$ ]]; then
    ALL_IMAGES=$(docker images -q)
    if [ ! -z "$ALL_IMAGES" ]; then
        docker rmi -f $ALL_IMAGES 2>/dev/null || true
        echo "✅ All Docker images removed"
    else
        echo "✅ No Docker images to remove"
    fi
else
    echo "⏭️  Docker images kept"
fi

# 6. Clean Docker system
echo "🧽 Running Docker system cleanup..."
docker system prune -af --volumes 2>/dev/null || true
echo "✅ Docker system cleaned"

# 7. Remove project log files and temporary data
echo "📄 Cleaning project files..."

# Remove log files
for log_file in ingestor.log monitoring_agent.log *.log; do
    if [ -f "$log_file" ]; then
        rm "$log_file"
        echo "   ✅ Removed $log_file"
    fi
done

# Remove SQLite test databases
for db_file in test_metrics.db *.db; do
    if [ -f "$db_file" ]; then
        rm "$db_file"
        echo "   ✅ Removed $db_file"
    fi
done

# Remove Python cache
if [ -d "__pycache__" ]; then
    rm -rf __pycache__
    echo "   ✅ Removed Python cache"
fi

# Remove .pyc files
find . -name "*.pyc" -delete 2>/dev/null || true
echo "   ✅ Removed Python bytecode files"

echo "✅ Project files cleaned"

# 8. Show final status
echo ""
echo "📊 Cleanup Summary:"
echo "==================="
echo "🐳 Docker Containers: $(docker ps -aq | wc -l | tr -d ' ') remaining"
echo "💾 Docker Volumes: $(docker volume ls -q | wc -l | tr -d ' ') remaining"
echo "🌐 Docker Networks: $(docker network ls -q | wc -l | tr -d ' ') remaining (includes defaults)"
echo "🖼️  Docker Images: $(docker images -q | wc -l | tr -d ' ') remaining"
echo "📡 Running Python Processes: $(ps aux | grep -E '(data_ingestor|platform_monitoring_agent)' | grep -v grep | wc -l | tr -d ' ')"

# 9. Show disk space freed
echo ""
echo "💿 Disk Space Status:"
echo "Docker space usage:"
docker system df 2>/dev/null || echo "Docker system info unavailable"

echo ""
echo "🎉 Complete cleanup finished!"
echo ""
echo "Next steps:"
echo "• To start fresh: ./start_all.sh"
echo "• To check what's running: docker ps && docker volume ls"
echo "• To see Docker space usage: docker system df"