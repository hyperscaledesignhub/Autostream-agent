"""
Web-based Chatbot Interface for Platform Monitoring
Streamlit-based chat interface for the monitoring agent
"""

import streamlit as st
import uuid
import time
import threading
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from typing import Dict, List

# Import monitoring agent components
from platform_monitoring_agent import (
    monitoring_agent, 
    check_real_time_anomalies,
    get_anomaly_summary,
    get_cross_component_anomalies,
    get_db_connection
)
from langchain_core.messages import HumanMessage

# Configure Streamlit page
st.set_page_config(
    page_title="Platform Monitoring Chatbot",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for chat interface
st.markdown("""
<style>
.user-message {
    background-color: #e3f2fd;
    padding: 10px;
    border-radius: 10px;
    margin: 5px 0;
    text-align: right;
}

.bot-message {
    background-color: #f5f5f5;
    padding: 10px;
    border-radius: 10px;
    margin: 5px 0;
    text-align: left;
}

.alert-critical {
    background-color: #ffebee;
    border-left: 5px solid #f44336;
    padding: 10px;
    margin: 10px 0;
}

.alert-warning {
    background-color: #fff3e0;
    border-left: 5px solid #ff9800;
    padding: 10px;
    margin: 10px 0;
}

.metric-card {
    background-color: white;
    padding: 15px;
    border-radius: 10px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    margin: 10px 0;
}
</style>
""", unsafe_allow_html=True)

def initialize_session():
    """Initialize session state variables"""
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    
    if 'thread_id' not in st.session_state:
        st.session_state.thread_id = str(uuid.uuid4())
    
    if 'agent_config' not in st.session_state:
        st.session_state.agent_config = {
            "configurable": {"thread_id": st.session_state.thread_id}
        }
    
    if 'auto_refresh' not in st.session_state:
        st.session_state.auto_refresh = False

def get_system_health_overview():
    """Get quick system health overview for dashboard"""
    try:
        # Get recent anomalies
        recent_anomalies = check_real_time_anomalies.invoke({'last_minutes': 5})
        
        # Count active anomalies by severity
        conn = get_db_connection()
        cur = conn.cursor()
        
        health_query = """
        SELECT 
            severity,
            COUNT(*) as count
        FROM anomaly_events
        WHERE time >= NOW() - INTERVAL '5 minutes'
        AND resolved_at IS NULL
        GROUP BY severity
        """
        
        cur.execute(health_query)
        anomaly_counts = cur.fetchall()
        
        critical_count = 0
        warning_count = 0
        
        for row in anomaly_counts:
            if row['severity'] == 'critical':
                critical_count = row['count']
            elif row['severity'] == 'warning':
                warning_count = row['count']
        
        # Component status
        component_query = """
        SELECT 
            component,
            COUNT(*) as active_anomalies
        FROM anomaly_events
        WHERE time >= NOW() - INTERVAL '10 minutes'
        AND resolved_at IS NULL
        GROUP BY component
        """
        
        cur.execute(component_query)
        component_status = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return {
            'critical_anomalies': critical_count,
            'warning_anomalies': warning_count,
            'component_status': {row['component']: row['active_anomalies'] for row in component_status},
            'total_anomalies': critical_count + warning_count,
            'last_updated': datetime.now()
        }
        
    except Exception as e:
        return {
            'error': str(e),
            'critical_anomalies': 0,
            'warning_anomalies': 0,
            'component_status': {},
            'total_anomalies': 0,
            'last_updated': datetime.now()
        }

def render_dashboard():
    """Render the system status dashboard"""
    st.subheader("🚥 System Health Dashboard")
    
    # Get health data
    health_data = get_system_health_overview()
    
    if 'error' in health_data:
        st.error(f"Dashboard Error: {health_data['error']}")
        return
    
    # Create metrics columns
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if health_data['critical_anomalies'] > 0:
            st.metric(
                "🔴 Critical", 
                health_data['critical_anomalies'],
                delta=f"{health_data['critical_anomalies']} active"
            )
        else:
            st.metric("🔴 Critical", "0", delta="All good")
    
    with col2:
        if health_data['warning_anomalies'] > 0:
            st.metric(
                "🟡 Warning", 
                health_data['warning_anomalies'],
                delta=f"{health_data['warning_anomalies']} active"
            )
        else:
            st.metric("🟡 Warning", "0", delta="All good")
    
    with col3:
        st.metric(
            "📊 Total Issues", 
            health_data['total_anomalies'],
            delta=f"Last 5 min"
        )
    
    with col4:
        if health_data['total_anomalies'] == 0:
            st.metric("💚 Status", "Healthy", delta="System OK")
        else:
            st.metric("❌ Status", "Issues", delta="Needs attention")
    
    # Component status
    if health_data['component_status']:
        st.subheader("📦 Component Status")
        
        comp_col1, comp_col2, comp_col3 = st.columns(3)
        
        components = ['kafka', 'flink', 'clickhouse']
        cols = [comp_col1, comp_col2, comp_col3]
        
        for i, component in enumerate(components):
            with cols[i]:
                issues = health_data['component_status'].get(component, 0)
                if issues == 0:
                    st.success(f"✅ {component.upper()}: Healthy")
                else:
                    st.error(f"⚠️ {component.upper()}: {issues} issues")
    
    # Auto-refresh toggle
    auto_refresh = st.checkbox("🔄 Auto-refresh (30s)", value=st.session_state.auto_refresh)
    st.session_state.auto_refresh = auto_refresh
    
    if auto_refresh:
        time.sleep(30)
        st.rerun()
    
    st.caption(f"Last updated: {health_data['last_updated'].strftime('%Y-%m-%d %H:%M:%S')}")

def render_chat_interface():
    """Render the chat interface"""
    st.subheader("💬 Platform Monitoring Chat")
    
    # Quick action buttons
    st.markdown("**Quick Actions:**")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("🚨 Current Status"):
            user_input = "Check current system status and any active anomalies"
            process_user_message(user_input)
    
    with col2:
        if st.button("📊 24h Summary"):
            user_input = "Give me a summary of anomalies from the last 24 hours"
            process_user_message(user_input)
    
    with col3:
        if st.button("🔗 Cross-Component"):
            user_input = "Check for cross-component anomaly patterns"
            process_user_message(user_input)
    
    with col4:
        if st.button("🧹 Clear Chat"):
            st.session_state.chat_history = []
            st.rerun()
    
    st.markdown("---")
    
    # Chat history container
    chat_container = st.container()
    
    # Display chat history
    with chat_container:
        for i, message in enumerate(st.session_state.chat_history):
            if message['type'] == 'user':
                st.markdown(
                    f'<div class="user-message"><strong>You:</strong> {message["content"]}</div>',
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f'<div class="bot-message"><strong>🤖 Agent:</strong><br>{message["content"]}</div>',
                    unsafe_allow_html=True
                )
    
    # Chat input
    user_input = st.text_input(
        "Ask about system status, anomalies, or metrics:",
        placeholder="e.g., 'How many Kafka anomalies in the last hour?'",
        key="chat_input"
    )
    
    if st.button("Send") and user_input:
        process_user_message(user_input)
        st.rerun()

def process_user_message(user_input: str):
    """Process user message and get agent response"""
    # Add user message to history
    st.session_state.chat_history.append({
        'type': 'user',
        'content': user_input,
        'timestamp': datetime.now()
    })
    
    # Show loading
    with st.spinner("🤖 Analyzing..."):
        try:
            # Get response from monitoring agent
            response = monitoring_agent.invoke(
                {"messages": [HumanMessage(user_input)]},
                config=st.session_state.agent_config
            )
            
            bot_response = response['messages'][-1].content
            
            # Add bot response to history
            st.session_state.chat_history.append({
                'type': 'bot',
                'content': bot_response,
                'timestamp': datetime.now()
            })
            
        except Exception as e:
            error_msg = f"Error processing request: {str(e)}"
            st.session_state.chat_history.append({
                'type': 'bot',
                'content': error_msg,
                'timestamp': datetime.now()
            })

def render_sidebar():
    """Render sidebar with additional info and controls"""
    st.sidebar.title("🤖 Monitoring Assistant")
    
    st.sidebar.markdown("""
    **Available Commands:**
    - Check current anomalies
    - Get historical summaries
    - Analyze metric trends
    - Detect cascade failures
    - Query specific components
    """)
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("📋 Example Questions")
    
    examples = [
        "What's the current system status?",
        "How many critical anomalies in last hour?",
        "Show Kafka metrics trend for 6 hours",
        "Any cascade failures detected?",
        "What's wrong with ClickHouse?",
        "Compare Flink performance vs yesterday"
    ]
    
    for example in examples:
        if st.sidebar.button(f"💡 {example}", key=f"example_{hash(example)}"):
            process_user_message(example)
    
    st.sidebar.markdown("---")
    st.sidebar.info(
        f"**Session ID:** `{st.session_state.thread_id[:8]}...`\n\n"
        f"**Chat Messages:** {len(st.session_state.chat_history)}"
    )

def main():
    """Main application"""
    # Initialize session
    initialize_session()
    
    # App title
    st.title("🚀 Platform Monitoring Chatbot")
    st.markdown("**Real-time monitoring for Kafka, Flink & ClickHouse**")
    
    # Create tabs
    tab1, tab2 = st.tabs(["💬 Chat Interface", "📊 Dashboard"])
    
    with tab1:
        render_chat_interface()
    
    with tab2:
        render_dashboard()
    
    # Render sidebar
    render_sidebar()

if __name__ == "__main__":
    main()