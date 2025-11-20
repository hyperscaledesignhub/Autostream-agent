from langgraph.graph import StateGraph, END
from typing import Dict, Any
import asyncio
from datetime import datetime

from models import AgentState, ActionResult, ComponentType
from llm_agents import LocalLLMAgent, MasterLLMAgent, ComponentAgent
from log_monitor import LogMonitor

class PlatformAgentWorkflow:
    def __init__(self):
        self.local_llm = LocalLLMAgent()
        self.master_llm = MasterLLMAgent()
        self.component_agents = {
            ComponentType.PULSAR: ComponentAgent(ComponentType.PULSAR),
            ComponentType.FLINK: ComponentAgent(ComponentType.FLINK),
            ComponentType.CLICKHOUSE: ComponentAgent(ComponentType.CLICKHOUSE)
        }
        
        # Build the workflow graph
        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> StateGraph:
        workflow = StateGraph(AgentState)
        
        # Define workflow nodes
        workflow.add_node("classify_error", self._classify_error_node)
        workflow.add_node("analyze_error", self._analyze_error_node)
        workflow.add_node("route_to_component", self._route_to_component_node)
        workflow.add_node("execute_actions", self._execute_actions_node)
        
        # Define the flow
        workflow.set_entry_point("classify_error")
        
        # Conditional routing after classification
        workflow.add_conditional_edges(
            "classify_error",
            self._should_analyze_error,
            {
                True: "analyze_error",
                False: END
            }
        )
        
        workflow.add_edge("analyze_error", "route_to_component")
        workflow.add_edge("route_to_component", "execute_actions")
        workflow.add_edge("execute_actions", END)
        
        return workflow.compile()
    
    async def _classify_error_node(self, state: AgentState) -> Dict[str, Any]:
        """Local LLM classifies if log entry is an error"""
        print("At the _classify_error_node")
        if not state.get("log_entry"):
            return {"current_step": "classification_failed"}
        
        classification = await self.local_llm.classify_error(state["log_entry"])
        
        return {
            "error_classification": classification,
            "current_step": "error_classified"
        }
    
    def _should_analyze_error(self, state: AgentState) -> bool:
        """Determine if error needs further analysis"""
        classification = state.get("error_classification")
        if not classification:
            return False
        return classification.is_error and classification.confidence > 0.6
    
    async def _analyze_error_node(self, state: AgentState) -> Dict[str, Any]:
        """Master LLM analyzes the error in detail"""
        print("At the _analyze_error_node")
        analysis = await self.master_llm.analyze_error(state["log_entry"])
        
        return {
            "error_analysis": analysis,
            "current_step": "error_analyzed"
        }
    
    async def _route_to_component_node(self, state: AgentState) -> Dict[str, Any]:
        """Route to appropriate component agent"""
        print("At the _route_to_component_node ")
        return {"current_step": "routed_to_component"}
    
    async def _execute_actions_node(self, state: AgentState) -> Dict[str, Any]:
        """Execute remedial actions via component agent"""
        print("At the _execute_actions_node ")
        error_analysis = state.get("error_analysis")
        if not error_analysis:
            return {"current_step": "execution_failed"}
        
        component_agent = self.component_agents.get(error_analysis.component)
        if not component_agent:
            return {"current_step": "component_agent_not_found"}
        
        # Execute remedial actions
        action_results = await component_agent.take_remedial_action(error_analysis)
        
        # Convert to ActionResult objects
        results = []
        for result in action_results:
            results.append(ActionResult(
                action_taken=result["action_taken"],
                success=result["success"],
                output=result["output"],
                timestamp=datetime.now()
            ))
        
        return {
            "action_results": results,
            "current_step": "actions_executed"
        }
    
    async def process_log_entry(self, log_entry) -> Dict[str, Any]:
        """Process a single log entry through the workflow"""
        initial_state = {
            "log_entry": log_entry,
            "error_classification": None,
            "error_analysis": None,
            "action_results": [],
            "current_step": "log_ingestion", 
            "retries": 0
        }
        
        try:
            # Run the workflow
            result = await self.workflow.ainvoke(initial_state)
            return result
        except Exception as e:
            print(f"Workflow execution error: {e}")
            return {
                "log_entry": log_entry,
                "error_classification": None,
                "error_analysis": None,
                "action_results": [],
                "current_step": "workflow_failed",
                "retries": 0
            }

# Extension system for future components
class ComponentAgentRegistry:
    _agents: Dict[str, type] = {}
    
    @classmethod
    def register_agent(cls, component_name: str, agent_class: type):
        """Register a new component agent"""
        cls._agents[component_name] = agent_class
    
    @classmethod
    def create_agent(cls, component_name: str) -> ComponentAgent:
        """Create an instance of a registered agent"""
        if component_name not in cls._agents:
            raise ValueError(f"No agent registered for component: {component_name}")
        return cls._agents[component_name](ComponentType(component_name))
    
    @classmethod
    def list_registered_agents(cls) -> list:
        """List all registered agent types"""
        return list(cls._agents.keys())

# Example of extending with new component
class KafkaAgent(ComponentAgent):
    def __init__(self, component_type: ComponentType):
        super().__init__(component_type)
        # Kafka-specific actions
        self.actions.update({
            "restart_kafka": "systemctl restart kafka",
            "check_topics": "kafka-topics.sh --list --bootstrap-server localhost:9092",
            "check_consumer_lag": "kafka-consumer-groups.sh --bootstrap-server localhost:9092 --describe --all-groups"
        })

# Register the new agent (this shows extensibility)
# ComponentAgentRegistry.register_agent("kafka", KafkaAgent)