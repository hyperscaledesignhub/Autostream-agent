"""
REST API Server for Platform Monitoring Agent
FastAPI-based API wrapper for easy integration
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, List
import uuid
from datetime import datetime
import threading
import asyncio

# Import monitoring agent components
from platform_monitoring_agent import (
    monitoring_agent,
    check_real_time_anomalies,
    get_anomaly_summary,
    query_metrics_trend,
    get_cross_component_anomalies,
    periodic_anomaly_monitor,
    MONITORING_ACTIVE
)
from langchain_core.messages import HumanMessage

# FastAPI app
app = FastAPI(
    title="Platform Monitoring API",
    description="REST API for Kafka, Flink, and ClickHouse monitoring",
    version="1.0.0"
)

# CORS middleware for web frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables
ACTIVE_SESSIONS = {}
MONITORING_THREAD = None

# Pydantic models
class ChatMessage(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    session_id: str
    timestamp: datetime

class AnomalyQuery(BaseModel):
    last_minutes: Optional[int] = 5

class SummaryQuery(BaseModel):
    hours: Optional[int] = 24

class TrendQuery(BaseModel):
    component: str
    metric_name: str
    hours: Optional[int] = 6

class CrossComponentQuery(BaseModel):
    hours: Optional[int] = 12

class SystemStatus(BaseModel):
    status: str
    critical_anomalies: int
    warning_anomalies: int
    total_anomalies: int
    components: Dict[str, str]
    last_updated: datetime

@app.on_event("startup")
async def startup_event():
    """Start background monitoring on startup"""
    global MONITORING_THREAD
    
    if MONITORING_THREAD is None or not MONITORING_THREAD.is_alive():
        MONITORING_THREAD = threading.Thread(
            target=periodic_anomaly_monitor,
            args=(30,),  # 30 second interval
            daemon=True
        )
        MONITORING_THREAD.start()
    
    print("✓ Platform Monitoring API started")
    print("✓ Background anomaly monitoring active")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global MONITORING_ACTIVE
    MONITORING_ACTIVE = False
    print("✓ Platform Monitoring API shutdown")

@app.get("/")
async def root():
    """API health check"""
    return {
        "message": "Platform Monitoring API",
        "version": "1.0.0",
        "status": "active",
        "endpoints": [
            "/chat",
            "/anomalies/current",
            "/anomalies/summary",
            "/metrics/trend",
            "/anomalies/patterns",
            "/system/status"
        ]
    }

@app.post("/chat", response_model=ChatResponse)
async def chat_with_agent(chat_request: ChatMessage):
    """
    Chat with the monitoring agent
    """
    try:
        # Get or create session
        session_id = chat_request.session_id or str(uuid.uuid4())
        
        if session_id not in ACTIVE_SESSIONS:
            ACTIVE_SESSIONS[session_id] = {
                "thread_id": str(uuid.uuid4()),
                "created_at": datetime.now(),
                "message_count": 0
            }
        
        session = ACTIVE_SESSIONS[session_id]
        session["message_count"] += 1
        
        # Create agent config
        config = {"configurable": {"thread_id": session["thread_id"]}}
        
        # Get response from agent
        response = monitoring_agent.invoke(
            {"messages": [HumanMessage(chat_request.message)]},
            config=config
        )
        
        agent_response = response['messages'][-1].content
        
        return ChatResponse(
            response=agent_response,
            session_id=session_id,
            timestamp=datetime.now()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")

@app.post("/anomalies/current")
async def get_current_anomalies(query: AnomalyQuery):
    """
    Get current anomalies from the last N minutes
    """
    try:
        result = check_real_time_anomalies.invoke({"last_minutes": query.last_minutes})
        
        return {
            "anomalies": result,
            "query_minutes": query.last_minutes,
            "timestamp": datetime.now()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Anomaly check error: {str(e)}")

@app.post("/anomalies/summary")
async def get_anomaly_summary_api(query: SummaryQuery):
    """
    Get anomaly summary for the last N hours
    """
    try:
        result = get_anomaly_summary.invoke({"hours": query.hours})
        
        return {
            "summary": result,
            "query_hours": query.hours,
            "timestamp": datetime.now()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Summary error: {str(e)}")

@app.post("/metrics/trend")
async def get_metric_trend(query: TrendQuery):
    """
    Get trend analysis for a specific metric
    """
    try:
        result = query_metrics_trend.invoke({
            "component": query.component,
            "metric_name": query.metric_name,
            "hours": query.hours
        })
        
        return {
            "trend": result,
            "component": query.component,
            "metric": query.metric_name,
            "query_hours": query.hours,
            "timestamp": datetime.now()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Trend analysis error: {str(e)}")

@app.post("/anomalies/patterns")
async def get_anomaly_patterns(query: CrossComponentQuery):
    """
    Get cross-component anomaly patterns
    """
    try:
        result = get_cross_component_anomalies.invoke({"hours": query.hours})
        
        return {
            "patterns": result,
            "query_hours": query.hours,
            "timestamp": datetime.now()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pattern analysis error: {str(e)}")

@app.get("/system/status", response_model=SystemStatus)
async def get_system_status():
    """
    Get overall system health status
    """
    try:
        # Get current anomalies
        current_anomalies = check_real_time_anomalies.invoke({"last_minutes": 5})
        
        # Parse anomalies (simple count)
        critical_count = current_anomalies.count("CRITICAL")
        warning_count = current_anomalies.count("WARNING") 
        total_count = critical_count + warning_count
        
        # Determine overall status
        if critical_count > 0:
            status = "CRITICAL"
        elif warning_count > 0:
            status = "WARNING"
        else:
            status = "HEALTHY"
        
        # Component status (simplified)
        components = {
            "kafka": "HEALTHY" if "kafka" not in current_anomalies.lower() else "ISSUES",
            "flink": "HEALTHY" if "flink" not in current_anomalies.lower() else "ISSUES",
            "clickhouse": "HEALTHY" if "clickhouse" not in current_anomalies.lower() else "ISSUES"
        }
        
        return SystemStatus(
            status=status,
            critical_anomalies=critical_count,
            warning_anomalies=warning_count,
            total_anomalies=total_count,
            components=components,
            last_updated=datetime.now()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Status check error: {str(e)}")

@app.get("/sessions")
async def get_active_sessions():
    """
    Get information about active chat sessions
    """
    return {
        "active_sessions": len(ACTIVE_SESSIONS),
        "sessions": {
            session_id: {
                "created_at": session["created_at"],
                "message_count": session["message_count"]
            }
            for session_id, session in ACTIVE_SESSIONS.items()
        }
    }

@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """
    Delete a specific chat session
    """
    if session_id in ACTIVE_SESSIONS:
        del ACTIVE_SESSIONS[session_id]
        return {"message": f"Session {session_id} deleted"}
    else:
        raise HTTPException(status_code=404, detail="Session not found")

@app.get("/health")
async def health_check():
    """
    API health endpoint
    """
    return {
        "status": "healthy",
        "monitoring_active": MONITORING_ACTIVE,
        "active_sessions": len(ACTIVE_SESSIONS),
        "timestamp": datetime.now()
    }

if __name__ == "__main__":
    import uvicorn
    
    # Run the API server
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )