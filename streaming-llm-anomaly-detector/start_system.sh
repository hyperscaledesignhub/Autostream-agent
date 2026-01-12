#!/bin/bash

# Platform Monitoring System Startup Script
# Starts TimescaleDB, data ingestor, and monitoring services

set -e  # Exit on any error

echo "🚀 Starting Platform Monitoring System"
echo "======================================"

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to wait for service to be ready
wait_for_service() {
    local service_name="$1"
    local check_command="$2"
    local max_attempts=30
    local attempt=1
    
    echo "⏳ Waiting for $service_name to be ready..."
    
    while [ $attempt -le $max_attempts ]; do
        if eval "$check_command" >/dev/null 2>&1; then
            echo "✅ $service_name is ready!"
            return 0
        fi
        
        echo "   Attempt $attempt/$max_attempts - $service_name not ready yet..."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    echo "❌ $service_name failed to start after $max_attempts attempts"
    return 1
}

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🧹 Cleaning up..."
    
    # Stop data ingestor if running
    if [ ! -z "$INGESTOR_PID" ]; then
        echo "   Stopping data ingestor (PID: $INGESTOR_PID)..."
        kill $INGESTOR_PID 2>/dev/null || true
    fi
    
    # Stop monitoring agent if running
    if [ ! -z "$AGENT_PID" ]; then
        echo "   Stopping monitoring agent (PID: $AGENT_PID)..."
        kill $AGENT_PID 2>/dev/null || true
    fi
    
    echo "✅ Cleanup completed"
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Check prerequisites
echo "🔍 Checking prerequisites..."

if ! command_exists docker; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command_exists python3; then
    echo "❌ Python 3 is not installed. Please install Python 3 first."
    exit 1
fi

if ! command_exists pip3; then
    echo "❌ pip3 is not installed. Please install pip3 first."
    exit 1
fi

echo "✅ Prerequisites check passed"

# Install Python dependencies if needed
echo "📦 Installing Python dependencies..."
if [ -f "requirements.txt" ]; then
    pip3 install -r requirements.txt > /dev/null 2>&1 || {
        echo "❌ Failed to install Python dependencies"
        exit 1
    }
    echo "✅ Python dependencies installed"
else
    echo "⚠️  requirements.txt not found, skipping dependency installation"
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found, copying from .env.example"
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "📝 Please edit .env file with your OpenAI API key before continuing"
        echo "   Press Enter when ready..."
        read
    else
        echo "❌ .env.example file not found"
        exit 1
    fi
fi

# Start TimescaleDB using Docker Compose
echo "🐳 Starting TimescaleDB..."
if [ -f "docker-compose.yml" ]; then
    # Stop any existing containers
    docker-compose down 2>/dev/null || true
    
    # Start TimescaleDB
    docker-compose up -d timescaledb
    
    # Wait for TimescaleDB to be ready
    wait_for_service "TimescaleDB" "docker exec platform-timescaledb pg_isready -U postgres -d metrics_db"
    
    echo "✅ TimescaleDB is running"
else
    echo "❌ docker-compose.yml not found"
    exit 1
fi

# Wait a bit more for full initialization
echo "⏳ Waiting for database initialization to complete..."
sleep 5

# Verify database schema
echo "🔍 Verifying database schema..."
DB_CHECK=$(docker exec platform-timescaledb psql -U postgres -d metrics_db -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_name='platform_metrics';" 2>/dev/null | tr -d ' ')

if [ "$DB_CHECK" = "1" ]; then
    echo "✅ Database schema is ready"
else
    echo "❌ Database schema not found. Check schema.sql initialization."
    exit 1
fi

# Start data ingestor
echo "📡 Starting data ingestor..."
if [ -f "data_ingestor.py" ]; then
    python3 data_ingestor.py > ingestor.log 2>&1 &
    INGESTOR_PID=$!
    
    # Give it a moment to start
    sleep 3
    
    # Check if it's still running
    if kill -0 $INGESTOR_PID 2>/dev/null; then
        echo "✅ Data ingestor started (PID: $INGESTOR_PID)"
        echo "   Log: tail -f ingestor.log"
    else
        echo "❌ Data ingestor failed to start"
        cat ingestor.log
        exit 1
    fi
else
    echo "❌ data_ingestor.py not found"
    exit 1
fi

# Wait for initial data ingestion
echo "⏳ Waiting for initial data ingestion..."
sleep 15

# Show system status
echo ""
echo "📊 System Status:"
echo "=================="

# Check Docker container
DOCKER_STATUS=$(docker ps --format "table {{.Names}}\t{{.Status}}" --filter "name=platform-timescaledb")
echo "🐳 Docker Container:"
echo "$DOCKER_STATUS"

# Check database stats
echo ""
echo "📈 Database Stats:"
DB_STATS=$(docker exec platform-timescaledb psql -U postgres -d metrics_db -c "
SELECT 
    'Total Metrics' as stat, COUNT(*)::text as value FROM platform_metrics
UNION ALL
SELECT 
    'Active Anomalies', COUNT(*)::text FROM anomaly_events WHERE resolved_at IS NULL
UNION ALL
SELECT 
    'Components', COUNT(DISTINCT component)::text FROM platform_metrics WHERE time >= NOW() - INTERVAL '5 minutes';
" 2>/dev/null)
echo "$DB_STATS"

echo ""
echo "🎯 Available Interfaces:"
echo "========================"
echo "1. 💬 Web Chatbot:     streamlit run chatbot_interface.py"
echo "2. 🌐 REST API:        python api_server.py"
echo "3. 💻 CLI Interface:   python platform_monitoring_agent.py"
echo ""

# Ask user which interface to start
echo "Which interface would you like to start? (1/2/3/none): "
read -r choice

case $choice in
    1)
        echo "🌐 Starting Streamlit web interface..."
        if command_exists streamlit; then
            echo "   Open your browser to: http://localhost:8501"
            streamlit run chatbot_interface.py
        else
            echo "❌ Streamlit not installed. Install with: pip install streamlit"
        fi
        ;;
    2)
        echo "🚀 Starting REST API server..."
        echo "   API docs available at: http://localhost:8000/docs"
        python3 api_server.py
        ;;
    3)
        echo "💻 Starting CLI interface..."
        python3 platform_monitoring_agent.py
        ;;
    *)
        echo "🎯 System is running in background mode"
        echo ""
        echo "📋 Management Commands:"
        echo "   Check logs:           tail -f ingestor.log"
        echo "   Database console:     docker exec -it platform-timescaledb psql -U postgres -d metrics_db"
        echo "   Stop system:          docker-compose down && pkill -f data_ingestor"
        echo ""
        echo "   Press Ctrl+C to stop all services"
        
        # Keep running until user stops
        while true; do
            sleep 60
            # Check if ingestor is still running
            if ! kill -0 $INGESTOR_PID 2>/dev/null; then
                echo "⚠️  Data ingestor stopped unexpectedly"
                break
            fi
        done
        ;;
esac

# Wait for user interrupt
wait