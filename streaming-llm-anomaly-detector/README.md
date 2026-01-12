# Platform Monitoring Chatbot System

A comprehensive monitoring system for Kafka, Flink, and ClickHouse with AI-powered anomaly detection and chatbot interface.

## Features

- **Real-time Anomaly Detection**: Monitors platform metrics and detects anomalies using LLM analysis
- **Web Chatbot Interface**: Streamlit-based chat interface for natural language queries
- **REST API**: FastAPI server for programmatic access
- **TimescaleDB Integration**: Efficient time-series data storage and querying
- **Cross-Component Analysis**: Detects cascade failures and resource exhaustion patterns
- **Historical Analysis**: Query trends and patterns over time

## Architecture

```
TimescaleDB → LangGraph Agent → Multiple Interfaces:
                              ├── Streamlit Chatbot
                              ├── REST API
                              └── CLI Interface
```

## Setup

### 1. Database Setup

First, set up TimescaleDB and create the schema:

```sql
-- See the schema in platform_monitoring_agent.py comments
CREATE TABLE platform_metrics (...);
CREATE TABLE anomaly_events (...);
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Environment Configuration

```bash
cp .env.example .env
# Edit .env with your credentials:
# - OpenAI API key
# - TimescaleDB connection details
```

### 4. Run the System

#### Option A: Web Chatbot Interface
```bash
streamlit run chatbot_interface.py
```
- Opens at: http://localhost:8501
- Features: Chat interface, real-time dashboard, auto-refresh

#### Option B: REST API Server
```bash
python api_server.py
```
- API at: http://localhost:8000
- Docs at: http://localhost:8000/docs

#### Option C: CLI Interface
```bash
python platform_monitoring_agent.py
```

## Usage Examples

### Web Chatbot Commands:
- "What's the current system status?"
- "How many anomalies occurred since 1 day?"
- "Show me Kafka issues from last 6 hours"
- "Are there any cascade failures?"
- "What's wrong with ClickHouse replication?"

### API Endpoints:
```bash
# Current anomalies
curl -X POST "http://localhost:8000/anomalies/current" \
     -H "Content-Type: application/json" \
     -d '{"last_minutes": 10}'

# 24-hour summary
curl -X POST "http://localhost:8000/anomalies/summary" \
     -H "Content-Type: application/json" \
     -d '{"hours": 24}'

# Chat with agent
curl -X POST "http://localhost:8000/chat" \
     -H "Content-Type: application/json" \
     -d '{"message": "Check system status", "session_id": "user123"}'
```

## Key Components

### 1. Metrics Definitions (`platform_metrics_definition.py`)
- 43 comprehensive metrics across Kafka, Flink, ClickHouse
- Anomaly thresholds and patterns
- Cross-component failure detection rules

### 2. LangGraph Agent (`platform_monitoring_agent.py`)
- **Tool 1**: `check_real_time_anomalies()` - Current system status
- **Tool 2**: `get_anomaly_summary()` - Historical analysis using materialized views
- **Tool 3**: `query_metrics_trend()` - Metric trend analysis
- **Tool 4**: `get_cross_component_anomalies()` - Pattern detection
- **Background Monitor**: Periodic anomaly checking

### 3. Web Interface (`chatbot_interface.py`)
- Streamlit-based chat interface
- Real-time dashboard with health metrics
- Quick action buttons
- Auto-refresh capabilities
- Chat history and session management

### 4. API Server (`api_server.py`)
- FastAPI-based REST API
- Session management
- CORS support for web frontends
- Background monitoring integration

## Monitoring Capabilities

### Real-time Monitoring:
- Checks every 30 seconds for critical anomalies
- Immediate alerts for system issues
- Component-level health status

### Historical Analysis:
- 24-hour anomaly summaries
- Trend analysis over custom time periods
- Cross-component pattern detection

### Question Examples:
- "How many Kafka consumer lag incidents yesterday?"
- "Show Flink checkpoint failure trends"
- "Are there any memory leaks in ClickHouse?"
- "Compare system performance vs last week"

## Anomaly Types Detected:

### Kafka:
- Under-replicated partitions
- Consumer lag spikes
- JVM memory issues
- Broker failures

### Flink:
- Job restart loops
- Checkpoint failures
- Backpressure issues
- Low throughput

### ClickHouse:
- Query performance degradation
- Replication lag
- Disk space issues
- Insert bottlenecks

### Cross-Component:
- Cascade failures (Kafka → Flink → ClickHouse)
- Resource exhaustion patterns
- Network partition detection

## Files Structure:

```
├── platform_metrics_definition.py    # Metrics definitions and thresholds
├── platform_metrics_generator.py     # Test data generator
├── platform_monitoring_agent.py      # Main LangGraph agent
├── chatbot_interface.py              # Streamlit web interface
├── api_server.py                     # FastAPI REST server
├── test_anomaly_detection.py         # Testing utilities
├── incident_qna_chatbot.py           # PDF-based incident analysis
├── requirements.txt                  # Dependencies
├── .env.example                      # Configuration template
└── data/                             # Document storage
```

## Integration:

The system can be integrated with:
- Grafana dashboards
- Slack/Teams notifications
- PagerDuty alerting
- Custom monitoring tools via REST API

Built with LangGraph, OpenAI, TimescaleDB, and Streamlit.