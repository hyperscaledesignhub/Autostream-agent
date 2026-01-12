"""
Platform Monitoring Agent using LangGraph and TimescaleDB
Monitors metrics in real-time and answers questions about anomalies
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
import asyncio
import threading
import time

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from typing_extensions import TypedDict
import functools
from langchain_core.messages import HumanMessage, SystemMessage

# Load environment variables
load_dotenv()

# TimescaleDB connection configuration
DB_CONFIG = {
    'host': os.getenv('TIMESCALE_HOST', 'localhost'),
    'port': os.getenv('TIMESCALE_PORT', 5432),
    'database': os.getenv('TIMESCALE_DB', 'metrics_db'),
    'user': os.getenv('TIMESCALE_USER', 'postgres'),
    'password': os.getenv('TIMESCALE_PASSWORD', 'password')
}

# Global variable to store latest anomalies
LATEST_ANOMALIES = []
MONITORING_ACTIVE = True

def get_db_connection():
    """Create a database connection"""
    return psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)

@tool
def check_real_time_anomalies(last_minutes: int = 5, component: str = None) -> str:
    """
    Check for real-time anomalies in the last N minutes.
    This tool continuously monitors the platform_metrics table for anomalies.
    
    Args:
        last_minutes: Number of minutes to look back (default 5)
        component: Optional - specific component ('kafka', 'flink', or 'clickhouse')
    
    Returns:
        String describing current anomalies or "No anomalies" if system is healthy
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Query for recent anomalies
        if component and component.lower() in ['kafka', 'flink', 'clickhouse']:
            # Component-specific query, limited to 3 latest
            query = """
            SELECT 
                time,
                component,
                metric_name,
                value,
                severity,
                reason
            FROM anomaly_events
            WHERE time >= NOW() - INTERVAL '%s minutes'
            AND component = %s
            AND resolved_at IS NULL
            ORDER BY time DESC
            LIMIT 3
            """
            cur.execute(query, (last_minutes, component.lower()))
        else:
            # All components query
            query = """
            SELECT 
                time,
                component,
                metric_name,
                value,
                severity,
                reason
            FROM anomaly_events
            WHERE time >= NOW() - INTERVAL '%s minutes'
            AND resolved_at IS NULL
            ORDER BY time DESC, severity DESC
            """
            cur.execute(query, (last_minutes,))
        
        anomalies = cur.fetchall()
        
        if not anomalies:
            if component:
                return f"✅ No anomalies detected for {component.upper()} in the last {last_minutes} minutes."
            else:
                return f"✅ No anomalies detected in the last {last_minutes} minutes. System is healthy."
        
        # Format anomalies
        if component:
            result = f"🚨 {component.upper()} ANOMALIES (Latest 3):\n"
            result += f"Showing {len(anomalies)} most recent anomalies for {component.upper()}:\n\n"
        else:
            result = f"🚨 ACTIVE ANOMALIES (last {last_minutes} minutes):\n"
            result += f"Found {len(anomalies)} active anomalies:\n\n"
        
        for anomaly in anomalies:
            result += f"[{anomaly['severity'].upper()}] {anomaly['component'].upper()}\n"
            result += f"  Metric: {anomaly['metric_name']}\n"
            result += f"  Value: {anomaly['value']}\n"
            result += f"  Reason: {anomaly['reason']}\n"
            result += f"  Time: {anomaly['time']}\n"
            result += "-" * 40 + "\n"
        
        cur.close()
        conn.close()
        
        return result
        
    except Exception as e:
        return f"Error checking anomalies: {str(e)}"

@tool
def get_anomaly_summary(hours: int = 24) -> str:
    """
    Get a summary of anomalies from the last N hours using materialized views.
    
    Args:
        hours: Number of hours to look back (default 24)
    
    Returns:
        Summary statistics of anomalies including count by component, severity, and trends
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Query anomaly summary
        summary_query = """
        SELECT 
            component,
            severity,
            COUNT(*) as anomaly_count,
            COUNT(DISTINCT metric_name) as unique_metrics,
            AVG(EXTRACT(EPOCH FROM (COALESCE(resolved_at, NOW()) - time))/60)::INTEGER as avg_duration_minutes
        FROM anomaly_events
        WHERE time >= NOW() - INTERVAL '%s hours'
        GROUP BY component, severity
        ORDER BY component, severity DESC
        """
        
        cur.execute(summary_query, (hours,))
        summary = cur.fetchall()
        
        if not summary:
            return f"No anomalies found in the last {hours} hours. System has been stable."
        
        # Format summary
        result = f"📊 ANOMALY SUMMARY (last {hours} hours):\n"
        result += "=" * 50 + "\n\n"
        
        total_anomalies = sum(row['anomaly_count'] for row in summary)
        result += f"Total Anomalies: {total_anomalies}\n\n"
        
        # Group by component
        components = {}
        for row in summary:
            comp = row['component']
            if comp not in components:
                components[comp] = {'critical': 0, 'warning': 0, 'metrics': 0, 'avg_duration': 0}
            
            components[comp][row['severity']] = row['anomaly_count']
            components[comp]['metrics'] = max(components[comp]['metrics'], row['unique_metrics'])
            components[comp]['avg_duration'] = row['avg_duration_minutes']
        
        # Display by component
        for comp, stats in components.items():
            result += f"{comp.upper()}:\n"
            result += f"  Critical: {stats['critical']} | Warning: {stats['warning']}\n"
            result += f"  Affected Metrics: {stats['metrics']}\n"
            result += f"  Avg Resolution Time: {stats['avg_duration']:.0f} minutes\n"
            result += "\n"
        
        # Get top anomalous metrics
        top_metrics_query = """
        SELECT 
            metric_name,
            component,
            COUNT(*) as occurrences
        FROM anomaly_events
        WHERE time >= NOW() - INTERVAL '%s hours'
        GROUP BY metric_name, component
        ORDER BY occurrences DESC
        LIMIT 5
        """
        
        cur.execute(top_metrics_query, (hours,))
        top_metrics = cur.fetchall()
        
        if top_metrics:
            result += "\nTop 5 Problematic Metrics:\n"
            for i, metric in enumerate(top_metrics, 1):
                result += f"  {i}. {metric['component']}/{metric['metric_name']}: {metric['occurrences']} occurrences\n"
        
        cur.close()
        conn.close()
        
        return result
        
    except Exception as e:
        return f"Error getting anomaly summary: {str(e)}"

@tool
def query_metrics_trend(component: str, metric_name: str, hours: int = 6) -> str:
    """
    Query the trend of a specific metric over time using materialized views.
    
    Args:
        component: Component name (kafka, flink, clickhouse)
        metric_name: Name of the metric
        hours: Number of hours to look back
    
    Returns:
        Trend analysis of the metric including min, max, avg values
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Query from materialized view for performance
        query = """
        SELECT 
            bucket,
            avg_value,
            min_value,
            max_value,
            sample_count
        FROM metrics_1min
        WHERE component = %s 
        AND metric_name = %s
        AND bucket >= NOW() - INTERVAL '%s hours'
        ORDER BY bucket DESC
        LIMIT 60
        """
        
        cur.execute(query, (component, metric_name, hours))
        data = cur.fetchall()
        
        if not data:
            return f"No data found for {component}/{metric_name} in the last {hours} hours"
        
        # Calculate statistics
        all_avg = [row['avg_value'] for row in data]
        overall_avg = sum(all_avg) / len(all_avg)
        overall_min = min(row['min_value'] for row in data)
        overall_max = max(row['max_value'] for row in data)
        
        # Check for trend
        recent_avg = sum(all_avg[:10]) / 10 if len(all_avg) >= 10 else all_avg[0]
        older_avg = sum(all_avg[-10:]) / 10 if len(all_avg) >= 10 else all_avg[-1]
        
        if recent_avg > older_avg * 1.2:
            trend = "📈 INCREASING"
        elif recent_avg < older_avg * 0.8:
            trend = "📉 DECREASING"
        else:
            trend = "➡️ STABLE"
        
        result = f"📊 METRIC TREND: {component}/{metric_name}\n"
        result += f"Time Range: Last {hours} hours\n"
        result += f"Trend: {trend}\n"
        result += f"Overall Stats:\n"
        result += f"  Average: {overall_avg:.2f}\n"
        result += f"  Min: {overall_min:.2f}\n"
        result += f"  Max: {overall_max:.2f}\n"
        result += f"  Latest: {data[0]['avg_value']:.2f}\n"
        
        cur.close()
        conn.close()
        
        return result
        
    except Exception as e:
        return f"Error querying metric trend: {str(e)}"

@tool
def get_cross_component_anomalies(hours: int = 12) -> str:
    """
    Detect cross-component anomaly patterns (cascade failures, resource exhaustion, etc.)
    
    Args:
        hours: Number of hours to analyze
    
    Returns:
        Analysis of cross-component anomaly patterns
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Query for concurrent anomalies across components
        query = """
        WITH time_windows AS (
            SELECT 
                time_bucket('5 minutes', time) as window,
                component,
                COUNT(*) as anomaly_count,
                ARRAY_AGG(DISTINCT metric_name) as metrics
            FROM anomaly_events
            WHERE time >= NOW() - INTERVAL '%s hours'
            GROUP BY window, component
        )
        SELECT 
            window,
            COUNT(DISTINCT component) as affected_components,
            SUM(anomaly_count) as total_anomalies,
            ARRAY_AGG(component ORDER BY component) as components
        FROM time_windows
        GROUP BY window
        HAVING COUNT(DISTINCT component) > 1
        ORDER BY window DESC
        """
        
        cur.execute(query, (hours,))
        patterns = cur.fetchall()
        
        if not patterns:
            return f"No cross-component anomaly patterns detected in the last {hours} hours"
        
        result = f"🔗 CROSS-COMPONENT ANOMALY PATTERNS (last {hours} hours):\n"
        result += "=" * 50 + "\n\n"
        
        cascade_failures = 0
        resource_exhaustions = 0
        
        for pattern in patterns:
            components = pattern['components']
            
            # Detect pattern type
            if 'kafka' in components and 'flink' in components:
                if 'clickhouse' in components:
                    pattern_type = "CASCADE FAILURE"
                    cascade_failures += 1
                else:
                    pattern_type = "PIPELINE ISSUE"
            elif pattern['total_anomalies'] > 10:
                pattern_type = "RESOURCE EXHAUSTION"
                resource_exhaustions += 1
            else:
                pattern_type = "CORRELATED ANOMALY"
            
            result += f"[{pattern_type}] at {pattern['window']}\n"
            result += f"  Affected: {', '.join(components)}\n"
            result += f"  Total Anomalies: {pattern['total_anomalies']}\n"
            result += "-" * 30 + "\n"
        
        # Summary
        result += f"\nPattern Summary:\n"
        result += f"  Cascade Failures: {cascade_failures}\n"
        result += f"  Resource Exhaustions: {resource_exhaustions}\n"
        result += f"  Total Cross-Component Events: {len(patterns)}\n"
        
        cur.close()
        conn.close()
        
        return result
        
    except Exception as e:
        return f"Error analyzing cross-component patterns: {str(e)}"

def periodic_anomaly_monitor(interval_seconds: int = 30):
    """
    Background thread that periodically checks for anomalies
    """
    global LATEST_ANOMALIES, MONITORING_ACTIVE
    
    while MONITORING_ACTIVE:
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Check for new critical anomalies
            query = """
            SELECT * FROM anomaly_events
            WHERE time >= NOW() - INTERVAL '1 minute'
            AND severity = 'critical'
            AND resolved_at IS NULL
            ORDER BY time DESC
            """
            
            cur.execute(query)
            new_anomalies = cur.fetchall()
            
            if new_anomalies:
                LATEST_ANOMALIES = new_anomalies
                print(f"\n🚨 ALERT: {len(new_anomalies)} new critical anomalies detected!")
                for anomaly in new_anomalies[:3]:  # Show top 3
                    print(f"  - {anomaly['component']}/{anomaly['metric_name']}: {anomaly['value']}")
            
            cur.close()
            conn.close()
            
        except Exception as e:
            print(f"Monitor error: {e}")
        
        time.sleep(interval_seconds)

# Setup LLM and Agent  
# Load environment variables
load_dotenv()

model = ChatOpenAI(
    model=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
    temperature=0.3
)

system_prompt = SystemMessage(content="""
You are a Platform Monitoring Specialist for a streaming data platform with Kafka, Flink, and ClickHouse.

Your responsibilities:
1. Monitor real-time metrics and detect anomalies
2. Provide summaries of anomaly patterns over time
3. Analyze cross-component issues and cascade failures
4. Answer questions about system health and performance
5. Alert on critical issues immediately

When analyzing anomalies:
- Always check current status first with real-time tool
- Provide historical context using summary tools
- Identify patterns and root causes
- Suggest remediation steps for critical issues

Use these severity guidelines:
- CRITICAL: Immediate action required (service down, data loss risk)
- WARNING: Attention needed (degraded performance, approaching limits)

Be concise but thorough. Prioritize critical issues.
""")

# Create tool list
tools = [
    check_real_time_anomalies,
    get_anomaly_summary,
    query_metrics_trend,
    get_cross_component_anomalies
]

# Define the agent state
class AgentState(TypedDict):
    messages: list
    
# Agent node function
def agent_node(state: AgentState):
    messages = state["messages"]
    
    # Add system prompt if not present
    if not messages or not isinstance(messages[0], SystemMessage):
        messages = [system_prompt] + messages
    
    response = model.invoke(messages)
    return {"messages": messages + [response]}

# Tool node function
def tool_node(state: AgentState):
    messages = state["messages"]
    last_message = messages[-1]
    
    # Simple tool routing based on message content
    content = last_message.content.lower()
    
    # Check for specific component mentions
    component = None
    if "kafka" in content:
        component = "kafka"
    elif "flink" in content:
        component = "flink"
    elif "clickhouse" in content:
        component = "clickhouse"
    
    if "real-time" in content or "current anomalies" in content or "anomalies" in content:
        if component:
            result = check_real_time_anomalies.invoke({"last_minutes": 5, "component": component})
        else:
            result = check_real_time_anomalies.invoke({"last_minutes": 5})
    elif "summary" in content or "anomaly summary" in content:
        result = get_anomaly_summary.invoke({"hours": 1})
    elif "trend" in content and component:
        if component == "kafka":
            result = query_metrics_trend.invoke({"component": "kafka", "metric_name": "kafka_consumer_lag", "minutes": 10})
        elif component == "flink":
            result = query_metrics_trend.invoke({"component": "flink", "metric_name": "flink_task_throughput", "minutes": 10})
        elif component == "clickhouse":
            result = query_metrics_trend.invoke({"component": "clickhouse", "metric_name": "clickhouse_query_duration", "minutes": 10})
    elif "cross" in content or "cross-component" in content:
        result = get_cross_component_anomalies.invoke({"minutes": 10})
    else:
        if component:
            result = check_real_time_anomalies.invoke({"last_minutes": 5, "component": component})
        else:
            result = check_real_time_anomalies.invoke({"last_minutes": 5})
    
    tool_message = HumanMessage(content=f"Tool Result: {result}")
    return {"messages": messages + [tool_message]}

# Conditional edge function  
def should_continue(state: AgentState):
    messages = state["messages"]
    last_message = messages[-1]
    
    # Check if this is the initial user message (needs tools)
    if len(messages) <= 2:  # System message + user message
        return "tools"
    
    # If we have tool results, the agent should give final response and end
    for msg in messages:
        if "Tool Result:" in msg.content:
            return END
    
    # If no tool results yet, call tools
    return "tools"

# Create the graph
workflow = StateGraph(AgentState)
workflow.add_node("agent", agent_node)
workflow.add_node("tools", tool_node)

workflow.add_edge(START, "agent")
workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
workflow.add_edge("tools", END)

# Create memory for conversation
checkpointer = MemorySaver()

# Compile the graph
monitoring_agent = workflow.compile(checkpointer=checkpointer)

def main():
    """
    Main application with periodic monitoring and interactive chat
    """
    global MONITORING_ACTIVE
    
    print("🚀 Platform Monitoring Agent")
    print("=" * 50)
    
    # Control background monitoring with environment variable or set directly
    ENABLE_BACKGROUND_MONITOR = os.getenv("ENABLE_BACKGROUND_MONITOR", "false").lower() == "true"
    
    if ENABLE_BACKGROUND_MONITOR:
        # Start background monitoring thread
        monitor_thread = threading.Thread(target=periodic_anomaly_monitor, args=(30,))
        monitor_thread.daemon = True
        monitor_thread.start()
        print("✓ Background anomaly monitoring started (30s interval)")
    else:
        print("📌 Background monitoring disabled - Interactive mode only")
        print("   (Set ENABLE_BACKGROUND_MONITOR=true to enable)")
    
    # Setup conversation
    import uuid
    thread_id = str(uuid.uuid4())
    
    print("\nAvailable Commands:")
    print("  'status' - Check all current anomalies")
    print("  'kafka' - Check Kafka anomalies (latest 3)")
    print("  'flink' - Check Flink anomalies (latest 3)")
    print("  'clickhouse' - Check ClickHouse anomalies (latest 3)")
    print("  'summary' - Get 24-hour summary")
    print("  'patterns' - Analyze cross-component patterns")
    print("  'exit' - Stop monitoring and quit")
    print("\nExamples:")
    print("  'Show kafka anomalies' - Shows latest 3 Kafka anomalies")
    print("  'What are flink issues?' - Shows latest 3 Flink anomalies")
    print("=" * 50)
    
    while True:
        user_input = input("\nYou: ")
        
        if user_input.lower() == 'exit':
            MONITORING_ACTIVE = False
            print("Stopping monitoring...")
            break
        
        # Quick commands
        if user_input.lower() == 'status':
            user_input = "Check for any current anomalies in the system"
        elif user_input.lower() == 'kafka':
            user_input = "Show me the kafka anomalies"
        elif user_input.lower() == 'flink':
            user_input = "Show me the flink anomalies"
        elif user_input.lower() == 'clickhouse':
            user_input = "Show me the clickhouse anomalies"
        elif user_input.lower() == 'summary':
            user_input = "Give me a summary of anomalies from the last 24 hours"
        elif user_input.lower() == 'patterns':
            user_input = "Check for any cross-component anomaly patterns"
        
        # Send to agent
        response = monitoring_agent.invoke(
            {"messages": [HumanMessage(content=user_input)]},
            config={"configurable": {"thread_id": thread_id}}
        )
        
        print(f"\nAgent: {response['messages'][-1].content}")

if __name__ == "__main__":
    main()