#!/bin/bash

# Stop All Infrastructure Script
# Stops all components of the Platform Monitoring System

set -e

echo "🛑 Stopping Platform Monitoring System"
echo "======================================="

# Function to check if process is running
check_process() {
    local process_name="$1"
    if pgrep -f "$process_name" > /dev/null; then
        return 0  # Process is running
    else
        return 1  # Process is not running
    fi
}

# Function to stop process gracefully
stop_process() {
    local process_name="$1"
    local display_name="$2"
    
    echo "🔍 Checking $display_name..."
    
    if check_process "$process_name"; then
        echo "   Stopping $display_name..."
        pkill -f "$process_name" || true
        
        # Wait a moment for graceful shutdown
        sleep 2
        
        # Force kill if still running
        if check_process "$process_name"; then
            echo "   Force stopping $display_name..."
            pkill -9 -f "$process_name" || true
            sleep 1
        fi
        
        if check_process "$process_name"; then
            echo "   ❌ Failed to stop $display_name"
        else
            echo "   ✅ $display_name stopped"
        fi
    else
        echo "   ✅ $display_name was not running"
    fi
}

# 1. Stop Python monitoring processes
echo -e "\n📡 Stopping Python Services:"
stop_process "data_ingestor.py" "Data Ingestor"
stop_process "platform_monitoring_agent.py" "Platform Monitoring Agent"
stop_process "api_server.py" "REST API Server"
stop_process "chatbot_interface.py" "Streamlit Chatbot"
stop_process "simple_monitoring_agent.py" "Simple Monitoring Agent"

# 2. Stop TimescaleDB Docker container
echo -e "\n🐳 Stopping Docker Services:"
if docker ps | grep -q timescaledb; then
    echo "   Stopping TimescaleDB container..."
    docker stop timescaledb || true
    echo "   ✅ TimescaleDB container stopped"
else
    echo "   ✅ TimescaleDB container was not running"
fi

# Optional: Remove container and its data (COMMENTED OUT - just stops container)
# echo "   Do you want to remove the container and its data? (y/N)"
# read -t 10 -p "   (auto-skip in 10s): " remove_container
# if [[ "$remove_container" =~ ^[Yy]$ ]]; then
#     echo "   Removing TimescaleDB container..."
#     docker rm timescaledb 2>/dev/null || true
#     echo "   ✅ Container removed"
# else
#     echo "   📦 Container preserved"
# fi

echo "   📦 Container stopped but preserved (data intact)"

# 3. Clean up log files (optional)
echo -e "\n🧹 Cleaning up log files:"
if [ -f "ingestor.log" ]; then
    rm ingestor.log
    echo "   ✅ Removed ingestor.log"
fi

if [ -f "monitoring_agent.log" ]; then
    rm monitoring_agent.log
    echo "   ✅ Removed monitoring_agent.log"
fi

# 4. Show final status
echo -e "\n📊 Final Status Check:"
echo "========================"

# Check remaining processes
REMAINING_PROCESSES=$(ps aux | grep -E "(data_ingestor|platform_monitoring_agent|api_server|chatbot_interface)" | grep -v grep | wc -l)
echo "Python processes still running: $REMAINING_PROCESSES"

# Check Docker containers
DOCKER_CONTAINERS=$(docker ps | grep timescaledb | wc -l)
echo "TimescaleDB containers running: $DOCKER_CONTAINERS"

if [ "$REMAINING_PROCESSES" -eq 0 ] && [ "$DOCKER_CONTAINERS" -eq 0 ]; then
    echo -e "\n🎉 All infrastructure stopped successfully!"
    echo "✅ System is completely shut down"
else
    echo -e "\n⚠️  Some components may still be running"
    echo "   Check manually with: ps aux | grep -E '(data_ingestor|platform_monitoring_agent)'"
fi

echo -e "\n💡 To restart everything, run: ./start_all.sh"