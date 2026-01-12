"""
Platform Metrics Generator for Kafka, Flink, and ClickHouse
Generates realistic metrics with normal and anomalous patterns
"""

import random
import time
from datetime import datetime
from typing import Dict, List, Optional
import json
from platform_metrics_definition import (
    KAFKA_METRICS, FLINK_METRICS, CLICKHOUSE_METRICS, 
    CROSS_COMPONENT_ANOMALIES, is_anomalous
)

class PlatformMetricsGenerator:
    def __init__(self, anomaly_probability: float = 0.1):
        self.anomaly_probability = anomaly_probability
        self.current_state = "normal"  # normal, degraded, critical
        self.anomaly_scenario = None
        self.scenario_duration = 0
        
    def generate_normal_metric(self, metric_def: Dict) -> float:
        """Generate a normal metric value within expected range"""
        normal_range = metric_def['normal_range']
        # Add some realistic variation
        if 'rate' in metric_def['unit'] or 'sec' in metric_def['unit']:
            # For rate metrics, use log-normal distribution for more realistic patterns
            mean = (normal_range['min'] + normal_range['max']) / 2
            value = random.lognormvariate(0, 0.3) * mean
            value = max(normal_range['min'], min(value, normal_range['max']))
        else:
            # For other metrics, use normal distribution
            mean = (normal_range['min'] + normal_range['max']) / 2
            std = (normal_range['max'] - normal_range['min']) / 6
            value = random.gauss(mean, std)
            value = max(normal_range['min'], min(value, normal_range['max']))
        return round(value, 2)
    
    def generate_anomalous_metric(self, metric_def: Dict, severity: str = "warning") -> float:
        """Generate an anomalous metric value"""
        if severity == "critical":
            if 'critical_threshold' in metric_def:
                threshold = metric_def['critical_threshold']
                # Generate value beyond critical threshold
                if metric_def.get('threshold_direction', 'above') == 'above':
                    value = threshold * random.uniform(1.1, 2.0)
                else:
                    value = threshold * random.uniform(0.1, 0.5)
            else:
                # No threshold defined, use extreme values
                normal_range = metric_def['normal_range']
                if random.choice([True, False]):
                    value = normal_range['max'] * random.uniform(2, 5)
                else:
                    value = normal_range['min'] * random.uniform(0.01, 0.1)
        else:  # warning
            if 'warning_threshold' in metric_def:
                threshold = metric_def['warning_threshold']
                if metric_def.get('threshold_direction', 'above') == 'above':
                    value = threshold * random.uniform(1.0, 1.3)
                else:
                    value = threshold * random.uniform(0.7, 1.0)
            else:
                normal_range = metric_def['normal_range']
                if random.choice([True, False]):
                    value = normal_range['max'] * random.uniform(1.2, 1.5)
                else:
                    value = normal_range['min'] * random.uniform(0.5, 0.8)
        
        return round(max(0, value), 2)  # Ensure non-negative
    
    def generate_cascade_failure_metrics(self) -> Dict:
        """Generate metrics showing a cascading failure pattern"""
        metrics = {}
        
        # Kafka starts failing
        metrics['kafka'] = {
            'kafka_broker_under_replicated_partitions': 15,
            'kafka_broker_offline_partitions': 3,
            'kafka_consumer_lag': 2500000,  # 2.5M messages
            'kafka_consumer_lag_seconds': 1200,  # 20 minutes
            'kafka_broker_request_handler_idle_percent': 2,  # Overloaded
        }
        
        # Flink is affected
        metrics['flink'] = {
            'flink_task_backpressure': 0.95,  # Severe backpressure
            'flink_jobmanager_job_restarts': 8,
            'flink_task_records_lag': 5000000,
            'flink_task_throughput': 50,  # Extremely low
            'flink_jobmanager_checkpoint_failure_rate': 45,
        }
        
        # ClickHouse struggles with inserts
        metrics['clickhouse'] = {
            'clickhouse_insert_latency': 5000,  # 5 seconds
            'clickhouse_inserts_per_second': 1000,  # Very low
            'clickhouse_background_pool_tasks': 250,  # Saturated
            'clickhouse_memory_usage': 92,
            'clickhouse_failed_queries': 15,
        }
        
        return metrics
    
    def generate_resource_exhaustion_metrics(self) -> Dict:
        """Generate metrics showing resource exhaustion"""
        metrics = {}
        
        # All components show high resource usage
        metrics['kafka'] = {
            'kafka_jvm_heap_usage': random.uniform(88, 95),
            'kafka_jvm_gc_pause_time': random.uniform(800, 1500),
            'kafka_broker_bytes_in_per_sec': 250000000,  # 250MB/s - very high
        }
        
        metrics['flink'] = {
            'flink_taskmanager_heap_used': random.uniform(90, 96),
            'flink_taskmanager_cpu_load': random.uniform(92, 98),
            'flink_jobmanager_checkpoint_size': 15000000000,  # 15GB
        }
        
        metrics['clickhouse'] = {
            'clickhouse_memory_usage': random.uniform(88, 94),
            'clickhouse_disk_usage': random.uniform(87, 93),
            'clickhouse_memory_tracked': random.uniform(180, 200),  # GB
        }
        
        return metrics
    
    def generate_normal_platform_metrics(self) -> Dict:
        """Generate normal metrics for all components"""
        metrics = {
            'kafka': {},
            'flink': {},
            'clickhouse': {}
        }
        
        # Generate normal Kafka metrics
        for metric_name, metric_def in random.sample(list(KAFKA_METRICS.items()), 
                                                      min(8, len(KAFKA_METRICS))):
            metrics['kafka'][metric_name] = self.generate_normal_metric(metric_def)
        
        # Generate normal Flink metrics
        for metric_name, metric_def in random.sample(list(FLINK_METRICS.items()), 
                                                      min(8, len(FLINK_METRICS))):
            metrics['flink'][metric_name] = self.generate_normal_metric(metric_def)
        
        # Generate normal ClickHouse metrics
        for metric_name, metric_def in random.sample(list(CLICKHOUSE_METRICS.items()), 
                                                      min(8, len(CLICKHOUSE_METRICS))):
            metrics['clickhouse'][metric_name] = self.generate_normal_metric(metric_def)
        
        return metrics
    
    def inject_component_anomalies(self, metrics: Dict, component: str, severity: str) -> Dict:
        """Inject anomalies into a specific component"""
        component_metrics = {
            'kafka': KAFKA_METRICS,
            'flink': FLINK_METRICS,
            'clickhouse': CLICKHOUSE_METRICS
        }
        
        if component in component_metrics:
            # Select 2-4 metrics to make anomalous
            num_anomalies = random.randint(2, 4)
            selected_metrics = random.sample(list(component_metrics[component].items()), 
                                           min(num_anomalies, len(component_metrics[component])))
            
            for metric_name, metric_def in selected_metrics:
                metrics[component][metric_name] = self.generate_anomalous_metric(metric_def, severity)
        
        return metrics
    
    def generate_metrics_batch(self) -> Dict:
        """Generate a complete batch of platform metrics"""
        # Decide if this batch should have anomalies
        inject_anomaly = random.random() < self.anomaly_probability
        
        if inject_anomaly:
            # Determine anomaly type
            anomaly_type = random.choice([
                'single_component',
                'cascade_failure',
                'resource_exhaustion',
                'cross_component'
            ])
            
            if anomaly_type == 'cascade_failure':
                metrics = self.generate_cascade_failure_metrics()
                # Add some normal metrics too
                normal_metrics = self.generate_normal_platform_metrics()
                for component in metrics:
                    for metric, value in normal_metrics[component].items():
                        if metric not in metrics[component]:
                            metrics[component][metric] = value
                anomaly_info = {
                    'type': 'cascade_failure',
                    'severity': 'critical',
                    'description': 'Cascading failure across Kafka -> Flink -> ClickHouse'
                }
                
            elif anomaly_type == 'resource_exhaustion':
                metrics = self.generate_resource_exhaustion_metrics()
                normal_metrics = self.generate_normal_platform_metrics()
                for component in metrics:
                    for metric, value in normal_metrics[component].items():
                        if metric not in metrics[component]:
                            metrics[component][metric] = value
                anomaly_info = {
                    'type': 'resource_exhaustion',
                    'severity': 'critical',
                    'description': 'System-wide resource exhaustion'
                }
                
            elif anomaly_type == 'single_component':
                metrics = self.generate_normal_platform_metrics()
                affected_component = random.choice(['kafka', 'flink', 'clickhouse'])
                severity = random.choice(['warning', 'critical'])
                metrics = self.inject_component_anomalies(metrics, affected_component, severity)
                anomaly_info = {
                    'type': 'single_component',
                    'severity': severity,
                    'affected_component': affected_component,
                    'description': f'{affected_component} experiencing {severity} issues'
                }
                
            else:  # cross_component
                metrics = self.generate_normal_platform_metrics()
                # Affect 2 components
                components = random.sample(['kafka', 'flink', 'clickhouse'], 2)
                for comp in components:
                    metrics = self.inject_component_anomalies(metrics, comp, 'warning')
                anomaly_info = {
                    'type': 'cross_component',
                    'severity': 'warning',
                    'affected_components': components,
                    'description': f'Multiple components affected: {", ".join(components)}'
                }
        else:
            metrics = self.generate_normal_platform_metrics()
            anomaly_info = None
        
        # Analyze metrics for anomalies
        detected_anomalies = {}
        for component in ['kafka', 'flink', 'clickhouse']:
            component_anomalies = []
            for metric_name, value in metrics[component].items():
                result = is_anomalous(component, metric_name, value)
                if result['is_anomaly']:
                    component_anomalies.append({
                        'metric': metric_name,
                        'value': value,
                        'severity': result['severity'],
                        'reason': result['reason']
                    })
            if component_anomalies:
                detected_anomalies[component] = component_anomalies
        
        return {
            'timestamp': datetime.now().isoformat(),
            'metrics': metrics,
            'metadata': {
                'environment': 'production',
                'cluster': 'main-cluster',
                'injected_anomaly': anomaly_info,
                'detected_anomalies': detected_anomalies if detected_anomalies else None
            }
        }
    
    def stream_metrics(self, interval_seconds: int = 5):
        """Continuously generate platform metrics"""
        while True:
            yield self.generate_metrics_batch()
            time.sleep(interval_seconds)

def main():
    """Test the platform metrics generator"""
    generator = PlatformMetricsGenerator(anomaly_probability=0.3)
    
    print("Platform Metrics Generator Test")
    print("=" * 80)
    
    for i in range(3):
        print(f"\nBatch {i+1}:")
        print("-" * 40)
        
        batch = generator.generate_metrics_batch()
        
        # Print summary
        print(f"Timestamp: {batch['timestamp']}")
        
        # Print sample metrics from each component
        for component in ['kafka', 'flink', 'clickhouse']:
            print(f"\n{component.upper()} Metrics:")
            for metric, value in list(batch['metrics'][component].items())[:3]:
                print(f"  {metric}: {value}")
        
        # Print anomaly information
        if batch['metadata']['injected_anomaly']:
            print(f"\n⚠️  Injected Anomaly:")
            print(f"  Type: {batch['metadata']['injected_anomaly']['type']}")
            print(f"  Severity: {batch['metadata']['injected_anomaly']['severity']}")
            print(f"  Description: {batch['metadata']['injected_anomaly']['description']}")
        
        if batch['metadata']['detected_anomalies']:
            print(f"\n🚨 Detected Anomalies:")
            for component, anomalies in batch['metadata']['detected_anomalies'].items():
                print(f"  {component}:")
                for anomaly in anomalies[:2]:  # Show first 2
                    print(f"    - {anomaly['metric']}: {anomaly['value']} ({anomaly['severity']})")
        
        time.sleep(2)

if __name__ == "__main__":
    main()