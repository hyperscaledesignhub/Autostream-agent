import random
import time
from datetime import datetime
from typing import Dict, List
import json

class DummyMetricsGenerator:
    def __init__(self):
        self.metrics_definitions = {
            "cpu_usage": {"min": 20, "max": 80, "unit": "%"},
            "memory_usage": {"min": 30, "max": 70, "unit": "%"},
            "request_latency": {"min": 50, "max": 200, "unit": "ms"},
            "error_rate": {"min": 0, "max": 5, "unit": "%"},
            "throughput": {"min": 100, "max": 500, "unit": "req/s"},
            "disk_io": {"min": 10, "max": 100, "unit": "MB/s"},
            "network_bandwidth": {"min": 50, "max": 300, "unit": "Mbps"},
            "active_connections": {"min": 10, "max": 100, "unit": "connections"}
        }
        self.anomaly_probability = 0.1  # 10% chance of anomaly
        
    def generate_normal_value(self, metric_config: Dict) -> float:
        """Generate normal metric value within expected range"""
        return round(random.uniform(metric_config["min"], metric_config["max"]), 2)
    
    def generate_anomaly_value(self, metric_config: Dict) -> float:
        """Generate anomalous metric value outside normal range"""
        if random.choice([True, False]):
            # Spike above normal
            return round(metric_config["max"] * random.uniform(1.5, 3.0), 2)
        else:
            # Drop below normal
            return round(metric_config["min"] * random.uniform(0.1, 0.5), 2)
    
    def generate_metrics_batch(self) -> Dict:
        """Generate a batch of metrics with potential anomalies"""
        metrics = {}
        is_anomaly = random.random() < self.anomaly_probability
        anomaly_metrics = []
        
        for metric_name, config in self.metrics_definitions.items():
            if is_anomaly and random.random() < 0.3:  # 30% chance this metric is anomalous
                metrics[metric_name] = {
                    "value": self.generate_anomaly_value(config),
                    "unit": config["unit"],
                    "expected_range": f"{config['min']}-{config['max']}"
                }
                anomaly_metrics.append(metric_name)
            else:
                metrics[metric_name] = {
                    "value": self.generate_normal_value(config),
                    "unit": config["unit"],
                    "expected_range": f"{config['min']}-{config['max']}"
                }
        
        return {
            "timestamp": datetime.now().isoformat(),
            "metrics": metrics,
            "metadata": {
                "host": "server-01",
                "environment": "production",
                "injected_anomaly": bool(anomaly_metrics),
                "anomaly_metrics": anomaly_metrics if anomaly_metrics else None
            }
        }
    
    def stream_metrics(self, interval_seconds: int = 5):
        """Continuously generate metrics at specified interval"""
        while True:
            yield self.generate_metrics_batch()
            time.sleep(interval_seconds)