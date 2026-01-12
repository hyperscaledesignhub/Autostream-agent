#!/bin/bash

# Start All Infrastructure Script
# Starts all components of the Platform Monitoring System

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

# Function to start service in background
start_background_service() {
    local script_name="$1"
    local service_name="$2"
    local log_file="$3"
    
    echo "📡 Starting $service_name..."
    
    if [ -f "$script_name" ]; then
        python3 "$script_name" > "$log_file" 2>&1 &
        local pid=$!
        
        # Give it a moment to start
        sleep 3
        
        # Check if it's still running
        if kill -0 $pid 2>/dev/null; then
            echo "✅ $service_name started (PID: $pid, Log: $log_file)"
            return 0
        else
            echo "❌ $service_name failed to start"
            if [ -f "$log_file" ]; then
                echo "Error log:"
                tail -10 "$log_file"
            fi
            return 1
        fi
    else
        echo "❌ $script_name not found"
        return 1
    fi
}

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

echo "✅ Prerequisites check passed"

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found"
    if [ -f ".env.example" ]; then
        echo "📝 Copying .env.example to .env"
        cp .env.example .env
        echo "❌ Please edit .env file with your OpenAI API key, then run this script again"
        exit 1
    else
        echo "❌ .env.example file not found"
        exit 1
    fi
fi

echo "✅ Environment file found"

# Check Python dependencies
echo "📦 Checking Python dependencies..."

# Check if key packages are already installed with working versions
if python3 -c "import langgraph, langchain_openai, openai; print('Dependencies OK')" >/dev/null 2>&1; then
    echo "✅ Python dependencies already installed and working"
else
    echo "📦 Installing Python dependencies..."
    if [ -f "requirements.txt" ]; then
        echo "   Running: pip3 install -r requirements.txt"
        pip3 install -r requirements.txt 2>&1
        if [ $? -eq 0 ]; then
            echo "✅ Python dependencies ready"
        else
            echo "❌ Failed to install Python dependencies"
            echo "   Check the error messages above for details"
            echo "   Note: If dependencies are already working, you can ignore this error"
        fi
    else
        echo "⚠️  requirements.txt not found, skipping dependency installation"
    fi
fi

# 1. Start TimescaleDB
echo -e "\n🐳 Starting TimescaleDB..."

# Stop any existing TimescaleDB containers
docker stop timescaledb 2>/dev/null || true
docker rm timescaledb 2>/dev/null || true

# Start TimescaleDB with regular docker run
echo "Creating TimescaleDB container..."
docker run -d \
    --name timescaledb \
    -e POSTGRES_DB=metrics_db \
    -e POSTGRES_USER=postgres \
    -e POSTGRES_PASSWORD=password \
    -p 5432:5432 \
    timescale/timescaledb:latest-pg17

if [ $? -eq 0 ]; then
    echo "✅ TimescaleDB container created"
    
    # Wait for TimescaleDB to be ready
    wait_for_service "TimescaleDB" "docker exec timescaledb pg_isready -U postgres -d metrics_db"
    
    echo "✅ TimescaleDB is running"
else
    echo "❌ Failed to create TimescaleDB container"
    exit 1
fi

# 2. Initialize database schema (if needed)
echo -e "\n🗄️  Checking database schema..."
DB_CHECK=$(docker exec timescaledb psql -U postgres -d metrics_db -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_name='platform_metrics';" 2>/dev/null | tr -d ' ' || echo "0")

if [ "$DB_CHECK" = "1" ]; then
    echo "✅ Database schema exists"
else
    echo "📊 Creating database schema..."
    if [ -f "schema.sql" ]; then
        docker exec -i timescaledb psql -U postgres -d metrics_db < schema.sql >/dev/null 2>&1
        echo "✅ Database schema created"
    else
        echo "❌ schema.sql not found"
        exit 1
    fi
fi

# 3. Start Data Ingestor
echo -e "\n📡 Starting Data Ingestor..."
if ! start_background_service "data_ingestor.py" "Data Ingestor" "ingestor.log"; then
    echo "❌ Failed to start Data Ingestor"
    exit 1
fi

# Wait for initial data ingestion
echo "⏳ Waiting for initial data ingestion (10 seconds)..."
sleep 10

# 4. Verify data is being ingested
echo -e "\n📊 Verifying data ingestion..."
METRIC_COUNT=$(docker exec timescaledb psql -U postgres -d metrics_db -t -c "SELECT COUNT(*) FROM platform_metrics WHERE time >= NOW() - INTERVAL '2 minutes';" 2>/dev/null | tr -d ' ' || echo "0")

if [ "$METRIC_COUNT" -gt "0" ]; then
    echo "✅ Data ingestion verified ($METRIC_COUNT recent metrics)"
else
    echo "⚠️  No recent metrics found, but ingestor is running"
fi

# 5. Show system status
echo -e "\n📊 System Status:"
echo "=================="

# Check Docker container
echo "🐳 Docker Containers:"
docker ps --format "table {{.Names}}\t{{.Status}}" --filter "name=timescaledb"

# Check processes
echo -e "\n📡 Running Services:"
if pgrep -f "data_ingestor.py" > /dev/null; then
    DATA_PID=$(pgrep -f "data_ingestor.py")
    echo "✅ Data Ingestor (PID: $DATA_PID)"
else
    echo "❌ Data Ingestor not running"
fi

# Check database stats
echo -e "\n📈 Database Stats:"
docker exec timescaledb psql -U postgres -d metrics_db -c "
SELECT 
    'Total Metrics' as stat, COUNT(*)::text as value FROM platform_metrics
UNION ALL
SELECT 
    'Active Anomalies', COUNT(*)::text FROM anomaly_events WHERE resolved_at IS NULL
UNION ALL
SELECT 
    'Components', COUNT(DISTINCT component)::text FROM platform_metrics WHERE time >= NOW() - INTERVAL '5 minutes';
" 2>/dev/null || echo "Database query failed"

echo -e "\n🎯 Available Interfaces:"
echo "========================"
echo "1. 💻 Interactive CLI:    python3 platform_monitoring_agent.py"
echo "2. 🌐 Web Dashboard:      python3 -m streamlit run chatbot_interface.py"
echo "3. 📡 REST API:           python3 api_server.py"
echo "4. 🧪 Simple Test:        python3 simple_monitoring_agent.py"
echo ""
echo "🛑 To stop everything:    ./stop_all.sh"

echo -e "\n🎉 Platform Monitoring System is ready!"
echo "Choose an interface above to start monitoring."