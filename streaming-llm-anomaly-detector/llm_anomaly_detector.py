import os
import json
from typing import Dict, Optional
from openai import OpenAI
from datetime import datetime

class LLMAnomalyDetector:
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-3.5-turbo"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY environment variable or pass api_key parameter.")
        
        self.model = model
        self.client = OpenAI(api_key=self.api_key)
        
        self.system_prompt = """You are an expert system administrator analyzing system metrics for anomalies.
        Your task is to determine if the provided metrics indicate an anomaly or normal behavior.
        
        Consider the following when analyzing:
        1. Values significantly outside the expected range
        2. Unusual patterns or combinations of metrics
        3. Sudden spikes or drops in values
        
        Respond with a JSON object containing:
        - "anomaly_detected": boolean
        - "confidence": percentage (0-100)
        - "anomalous_metrics": list of metric names showing anomalies
        - "explanation": brief explanation of your findings
        """
        
        self.user_prompt_template = """
        Analyze the following system metrics for anomalies:
        
        Timestamp: {timestamp}
        Host: {host}
        Environment: {environment}
        
        Metrics:
        {metrics_formatted}
        
        Please determine if these metrics indicate normal operation or an anomaly.
        """
    
    def format_metrics(self, metrics: Dict) -> str:
        """Format metrics for LLM prompt"""
        formatted = []
        for name, data in metrics.items():
            formatted.append(
                f"- {name}: {data['value']} {data['unit']} "
                f"(expected range: {data['expected_range']})"
            )
        return "\n".join(formatted)
    
    def detect_anomaly_with_llm(self, metrics_batch: Dict) -> Dict:
        """Send metrics to LLM for anomaly detection"""
        user_prompt = self.user_prompt_template.format(
            timestamp=metrics_batch["timestamp"],
            host=metrics_batch["metadata"]["host"],
            environment=metrics_batch["metadata"]["environment"],
            metrics_formatted=self.format_metrics(metrics_batch["metrics"])
        )
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        result["detection_method"] = "OpenAI LLM"
        result["model"] = self.model
        return result
    
    def analyze_stream(self, metrics_batch: Dict) -> Dict:
        """Main method to analyze a metrics batch"""
        detection_result = self.detect_anomaly_with_llm(metrics_batch)
        
        return {
            "timestamp": metrics_batch["timestamp"],
            "host": metrics_batch["metadata"]["host"],
            "detection": detection_result,
            "metrics_summary": {
                name: data["value"] 
                for name, data in metrics_batch["metrics"].items()
            }
        }