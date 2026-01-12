"""
Platform Metrics Definition for Kafka, Flink, and ClickHouse
Defines normal ranges, anomaly thresholds, and patterns for each component
"""

# KAFKA METRICS
KAFKA_METRICS = {
    # Broker Metrics
    "kafka_broker_under_replicated_partitions": {
        "description": "Number of under-replicated partitions",
        "unit": "count",
        "normal_range": {"min": 0, "max": 0},
        "warning_threshold": 1,
        "critical_threshold": 5,
        "anomaly_conditions": ["value > 0 for more than 5 minutes"]
    },
    "kafka_broker_offline_partitions": {
        "description": "Number of offline partitions",
        "unit": "count",
        "normal_range": {"min": 0, "max": 0},
        "warning_threshold": 1,
        "critical_threshold": 1,
        "anomaly_conditions": ["value > 0"]
    },
    "kafka_broker_messages_in_per_sec": {
        "description": "Incoming message rate",
        "unit": "msg/sec",
        "normal_range": {"min": 1000, "max": 50000},
        "warning_threshold": 75000,
        "critical_threshold": 100000,
        "anomaly_conditions": [
            "sudden drop > 50% from baseline",
            "value < 100 (unless during maintenance)",
            "sustained spike > 2x normal peak"
        ]
    },
    "kafka_broker_bytes_in_per_sec": {
        "description": "Incoming bytes rate",
        "unit": "bytes/sec",
        "normal_range": {"min": 1048576, "max": 104857600},  # 1MB/s to 100MB/s
        "warning_threshold": 157286400,  # 150MB/s
        "critical_threshold": 209715200,  # 200MB/s
        "anomaly_conditions": ["rate > network capacity", "sudden drop > 70%"]
    },
    "kafka_broker_bytes_out_per_sec": {
        "description": "Outgoing bytes rate",
        "unit": "bytes/sec",
        "normal_range": {"min": 1048576, "max": 209715200},  # 1MB/s to 200MB/s
        "warning_threshold": 314572800,  # 300MB/s
        "critical_threshold": 419430400,  # 400MB/s
        "anomaly_conditions": ["rate > 2x input rate for extended period"]
    },
    "kafka_broker_request_handler_idle_percent": {
        "description": "Request handler thread idle percentage",
        "unit": "%",
        "normal_range": {"min": 20, "max": 80},
        "warning_threshold": 10,
        "critical_threshold": 5,
        "anomaly_conditions": ["value < 10% indicates overload"]
    },
    "kafka_broker_network_processor_idle_percent": {
        "description": "Network processor thread idle percentage",
        "unit": "%",
        "normal_range": {"min": 30, "max": 90},
        "warning_threshold": 20,
        "critical_threshold": 10,
        "anomaly_conditions": ["value < 20% indicates network bottleneck"]
    },
    
    # Consumer Lag Metrics
    "kafka_consumer_lag": {
        "description": "Consumer group lag",
        "unit": "messages",
        "normal_range": {"min": 0, "max": 10000},
        "warning_threshold": 50000,
        "critical_threshold": 100000,
        "anomaly_conditions": [
            "continuously increasing lag",
            "lag > 1 million messages",
            "lag growth rate > 1000 msg/sec"
        ]
    },
    "kafka_consumer_lag_seconds": {
        "description": "Consumer lag in time",
        "unit": "seconds",
        "normal_range": {"min": 0, "max": 60},
        "warning_threshold": 300,  # 5 minutes
        "critical_threshold": 600,  # 10 minutes
        "anomaly_conditions": ["lag > 10 minutes for real-time processing"]
    },
    
    # Partition Metrics
    "kafka_partition_leader_election_rate": {
        "description": "Leader election rate",
        "unit": "elections/sec",
        "normal_range": {"min": 0, "max": 0.1},
        "warning_threshold": 0.5,
        "critical_threshold": 1,
        "anomaly_conditions": ["frequent elections indicate instability"]
    },
    "kafka_partition_isr_shrink_rate": {
        "description": "In-Sync Replica shrink rate",
        "unit": "shrinks/sec",
        "normal_range": {"min": 0, "max": 0.01},
        "warning_threshold": 0.1,
        "critical_threshold": 0.5,
        "anomaly_conditions": ["high shrink rate indicates replica issues"]
    },
    
    # JVM Metrics for Kafka
    "kafka_jvm_heap_usage": {
        "description": "JVM heap memory usage",
        "unit": "%",
        "normal_range": {"min": 30, "max": 70},
        "warning_threshold": 80,
        "critical_threshold": 90,
        "anomaly_conditions": ["sustained > 85%", "frequent GC pauses"]
    },
    "kafka_jvm_gc_pause_time": {
        "description": "Garbage collection pause time",
        "unit": "ms",
        "normal_range": {"min": 0, "max": 100},
        "warning_threshold": 200,
        "critical_threshold": 500,
        "anomaly_conditions": ["pause > 1 second", "frequent long pauses"]
    }
}

# FLINK METRICS
FLINK_METRICS = {
    # Job Manager Metrics
    "flink_jobmanager_job_uptime": {
        "description": "Job uptime",
        "unit": "seconds",
        "normal_range": {"min": 3600, "max": float('inf')},
        "warning_threshold": 1800,  # Job running less than 30 min
        "critical_threshold": 300,   # Job running less than 5 min
        "anomaly_conditions": ["frequent restarts", "uptime < 5 minutes"]
    },
    "flink_jobmanager_job_restarts": {
        "description": "Number of job restarts",
        "unit": "count",
        "normal_range": {"min": 0, "max": 2},
        "warning_threshold": 5,
        "critical_threshold": 10,
        "anomaly_conditions": ["restart loop", "> 3 restarts in 10 minutes"]
    },
    "flink_jobmanager_checkpoint_duration": {
        "description": "Checkpoint duration",
        "unit": "ms",
        "normal_range": {"min": 100, "max": 5000},
        "warning_threshold": 10000,
        "critical_threshold": 30000,
        "anomaly_conditions": [
            "checkpoint timeout",
            "duration > 1 minute",
            "increasing trend"
        ]
    },
    "flink_jobmanager_checkpoint_size": {
        "description": "Checkpoint size",
        "unit": "bytes",
        "normal_range": {"min": 1048576, "max": 1073741824},  # 1MB to 1GB
        "warning_threshold": 5368709120,  # 5GB
        "critical_threshold": 10737418240,  # 10GB
        "anomaly_conditions": ["rapid growth", "size > 10GB"]
    },
    "flink_jobmanager_checkpoint_failure_rate": {
        "description": "Checkpoint failure rate",
        "unit": "%",
        "normal_range": {"min": 0, "max": 5},
        "warning_threshold": 10,
        "critical_threshold": 20,
        "anomaly_conditions": ["> 20% failure rate", "consecutive failures"]
    },
    
    # Task Manager Metrics
    "flink_taskmanager_heap_used": {
        "description": "Task manager heap usage",
        "unit": "%",
        "normal_range": {"min": 20, "max": 70},
        "warning_threshold": 80,
        "critical_threshold": 90,
        "anomaly_conditions": ["memory leak pattern", "OOM risk"]
    },
    "flink_taskmanager_cpu_load": {
        "description": "Task manager CPU load",
        "unit": "%",
        "normal_range": {"min": 20, "max": 70},
        "warning_threshold": 85,
        "critical_threshold": 95,
        "anomaly_conditions": ["sustained > 90%", "uneven distribution"]
    },
    "flink_taskmanager_network_io": {
        "description": "Network I/O rate",
        "unit": "MB/s",
        "normal_range": {"min": 10, "max": 500},
        "warning_threshold": 800,
        "critical_threshold": 1000,
        "anomaly_conditions": ["network saturation", "sudden drops"]
    },
    
    # Stream Processing Metrics
    "flink_task_backpressure": {
        "description": "Task backpressure",
        "unit": "ratio",
        "normal_range": {"min": 0, "max": 0.1},
        "warning_threshold": 0.5,
        "critical_threshold": 0.8,
        "anomaly_conditions": [
            "high backpressure > 0.5",
            "cascading backpressure",
            "persistent backpressure"
        ]
    },
    "flink_task_records_lag": {
        "description": "Records lag",
        "unit": "records",
        "normal_range": {"min": 0, "max": 10000},
        "warning_threshold": 100000,
        "critical_threshold": 1000000,
        "anomaly_conditions": ["continuously increasing", "lag > capacity"]
    },
    "flink_task_throughput": {
        "description": "Records processed per second",
        "unit": "records/sec",
        "normal_range": {"min": 1000, "max": 100000},
        "warning_threshold": 150000,
        "critical_threshold": 200000,
        "anomaly_conditions": [
            "throughput < 100 records/sec",
            "sudden drop > 50%",
            "zero throughput"
        ]
    },
    "flink_task_latency": {
        "description": "Processing latency",
        "unit": "ms",
        "normal_range": {"min": 10, "max": 100},
        "warning_threshold": 500,
        "critical_threshold": 1000,
        "anomaly_conditions": ["latency > SLA", "increasing trend"]
    },
    
    # Watermark Metrics
    "flink_watermark_lag": {
        "description": "Watermark lag",
        "unit": "ms",
        "normal_range": {"min": 0, "max": 1000},
        "warning_threshold": 5000,
        "critical_threshold": 10000,
        "anomaly_conditions": ["watermark stuck", "lag > window size"]
    }
}

# CLICKHOUSE METRICS
CLICKHOUSE_METRICS = {
    # Query Performance Metrics
    "clickhouse_query_duration": {
        "description": "Query execution time",
        "unit": "ms",
        "normal_range": {"min": 1, "max": 1000},
        "warning_threshold": 5000,
        "critical_threshold": 10000,
        "anomaly_conditions": [
            "query timeout",
            "duration > 30 seconds",
            "10x slower than baseline"
        ]
    },
    "clickhouse_queries_per_second": {
        "description": "Query rate",
        "unit": "queries/sec",
        "normal_range": {"min": 10, "max": 1000},
        "warning_threshold": 2000,
        "critical_threshold": 3000,
        "anomaly_conditions": ["rate exceeds connection pool", "sudden spike"]
    },
    "clickhouse_slow_queries": {
        "description": "Number of slow queries",
        "unit": "count/min",
        "normal_range": {"min": 0, "max": 5},
        "warning_threshold": 10,
        "critical_threshold": 20,
        "anomaly_conditions": ["> 20 slow queries per minute"]
    },
    "clickhouse_failed_queries": {
        "description": "Failed query rate",
        "unit": "%",
        "normal_range": {"min": 0, "max": 1},
        "warning_threshold": 5,
        "critical_threshold": 10,
        "anomaly_conditions": ["error rate > 10%", "specific error patterns"]
    },
    
    # Storage Metrics
    "clickhouse_disk_usage": {
        "description": "Disk space usage",
        "unit": "%",
        "normal_range": {"min": 20, "max": 70},
        "warning_threshold": 80,
        "critical_threshold": 90,
        "anomaly_conditions": ["rapid growth", "approaching capacity"]
    },
    "clickhouse_parts_count": {
        "description": "Number of data parts",
        "unit": "count",
        "normal_range": {"min": 100, "max": 10000},
        "warning_threshold": 50000,
        "critical_threshold": 100000,
        "anomaly_conditions": ["too many parts", "merge throttling"]
    },
    "clickhouse_merge_time": {
        "description": "Background merge time",
        "unit": "seconds",
        "normal_range": {"min": 0.1, "max": 10},
        "warning_threshold": 30,
        "critical_threshold": 60,
        "anomaly_conditions": ["merge taking > 1 minute", "merge queue growing"]
    },
    "clickhouse_replication_lag": {
        "description": "Replication lag in seconds",
        "unit": "seconds",
        "normal_range": {"min": 0, "max": 5},
        "warning_threshold": 30,
        "critical_threshold": 60,
        "anomaly_conditions": ["lag > 1 minute", "increasing lag"]
    },
    "clickhouse_replication_queue_size": {
        "description": "Replication queue size",
        "unit": "tasks",
        "normal_range": {"min": 0, "max": 100},
        "warning_threshold": 500,
        "critical_threshold": 1000,
        "anomaly_conditions": ["queue growing", "stuck tasks"]
    },
    
    # Memory Metrics
    "clickhouse_memory_usage": {
        "description": "Memory usage",
        "unit": "%",
        "normal_range": {"min": 20, "max": 60},
        "warning_threshold": 80,
        "critical_threshold": 90,
        "anomaly_conditions": ["OOM killer risk", "memory leak"]
    },
    "clickhouse_memory_tracked": {
        "description": "Tracked memory by queries",
        "unit": "GB",
        "normal_range": {"min": 1, "max": 50},
        "warning_threshold": 100,
        "critical_threshold": 150,
        "anomaly_conditions": ["exceeds available RAM", "runaway query"]
    },
    
    # Connection Metrics
    "clickhouse_connections": {
        "description": "Active connections",
        "unit": "count",
        "normal_range": {"min": 10, "max": 500},
        "warning_threshold": 800,
        "critical_threshold": 1000,
        "anomaly_conditions": ["connection pool exhaustion", "connection leaks"]
    },
    "clickhouse_http_connections": {
        "description": "HTTP connections",
        "unit": "count",
        "normal_range": {"min": 5, "max": 200},
        "warning_threshold": 400,
        "critical_threshold": 500,
        "anomaly_conditions": ["HTTP endpoint overload"]
    },
    
    # Insert Performance
    "clickhouse_inserts_per_second": {
        "description": "Insert rate",
        "unit": "rows/sec",
        "normal_range": {"min": 10000, "max": 1000000},
        "warning_threshold": 2000000,
        "critical_threshold": 3000000,
        "anomaly_conditions": ["insert bottleneck", "batch size issues"]
    },
    "clickhouse_insert_latency": {
        "description": "Insert latency",
        "unit": "ms",
        "normal_range": {"min": 10, "max": 100},
        "warning_threshold": 500,
        "critical_threshold": 1000,
        "anomaly_conditions": ["high latency inserts", "blocking inserts"]
    },
    
    # Background Operations
    "clickhouse_background_pool_tasks": {
        "description": "Background pool tasks",
        "unit": "count",
        "normal_range": {"min": 0, "max": 50},
        "warning_threshold": 100,
        "critical_threshold": 200,
        "anomaly_conditions": ["pool saturation", "stuck tasks"]
    }
}

# PLATFORM-WIDE ANOMALY PATTERNS
CROSS_COMPONENT_ANOMALIES = {
    "cascade_failure": {
        "description": "Cascading failure across components",
        "indicators": [
            "Kafka consumer lag increases AND Flink backpressure high",
            "Flink checkpoint failures AND ClickHouse insert latency increases",
            "Kafka broker offline AND Flink job restarts"
        ]
    },
    "data_pipeline_blockage": {
        "description": "Data pipeline is blocked",
        "indicators": [
            "Kafka consumer lag > 1M messages",
            "Flink throughput < 100 records/sec",
            "ClickHouse insert queue growing"
        ]
    },
    "resource_exhaustion": {
        "description": "System resources exhausted",
        "indicators": [
            "All components showing > 85% memory usage",
            "CPU throttling across services",
            "Disk space < 10% on any component"
        ]
    },
    "network_partition": {
        "description": "Network connectivity issues",
        "indicators": [
            "Kafka ISR shrinking",
            "Flink checkpoint timeouts",
            "ClickHouse replication lag increasing"
        ]
    },
    "coordinated_attack": {
        "description": "Possible DDoS or coordinated issue",
        "indicators": [
            "Sudden spike in all input metrics",
            "Connection pools exhausted",
            "Query/request rates 10x normal"
        ]
    }
}

# ANOMALY DETECTION RULES
def is_anomalous(component, metric_name, value, duration_minutes=5):
    """
    Determine if a metric value is anomalous
    
    Args:
        component: 'kafka', 'flink', or 'clickhouse'
        metric_name: Name of the metric
        value: Current metric value
        duration_minutes: How long the condition has persisted
    
    Returns:
        dict: {
            'is_anomaly': bool,
            'severity': 'normal'|'warning'|'critical',
            'reason': str
        }
    """
    metrics_dict = {
        'kafka': KAFKA_METRICS,
        'flink': FLINK_METRICS,
        'clickhouse': CLICKHOUSE_METRICS
    }
    
    if component not in metrics_dict:
        return {'is_anomaly': False, 'severity': 'normal', 'reason': 'Unknown component'}
    
    metrics = metrics_dict[component]
    if metric_name not in metrics:
        return {'is_anomaly': False, 'severity': 'normal', 'reason': 'Unknown metric'}
    
    metric_def = metrics[metric_name]
    normal_range = metric_def['normal_range']
    
    # Check if value is in normal range
    if normal_range['min'] <= value <= normal_range['max']:
        return {'is_anomaly': False, 'severity': 'normal', 'reason': 'Within normal range'}
    
    # Check warning threshold
    if 'warning_threshold' in metric_def:
        if metric_def.get('threshold_direction', 'above') == 'above':
            if value >= metric_def['warning_threshold']:
                if value >= metric_def.get('critical_threshold', float('inf')):
                    return {
                        'is_anomaly': True,
                        'severity': 'critical',
                        'reason': f'Value {value} exceeds critical threshold {metric_def["critical_threshold"]}'
                    }
                return {
                    'is_anomaly': True,
                    'severity': 'warning',
                    'reason': f'Value {value} exceeds warning threshold {metric_def["warning_threshold"]}'
                }
        else:  # below threshold
            if value <= metric_def['warning_threshold']:
                if value <= metric_def.get('critical_threshold', 0):
                    return {
                        'is_anomaly': True,
                        'severity': 'critical',
                        'reason': f'Value {value} below critical threshold {metric_def["critical_threshold"]}'
                    }
                return {
                    'is_anomaly': True,
                    'severity': 'warning',
                    'reason': f'Value {value} below warning threshold {metric_def["warning_threshold"]}'
                }
    
    # Check specific anomaly conditions
    for condition in metric_def.get('anomaly_conditions', []):
        # This would need more complex evaluation in practice
        if duration_minutes > 5:
            return {
                'is_anomaly': True,
                'severity': 'warning',
                'reason': f'Condition detected: {condition}'
            }
    
    return {'is_anomaly': False, 'severity': 'normal', 'reason': 'No anomaly detected'}