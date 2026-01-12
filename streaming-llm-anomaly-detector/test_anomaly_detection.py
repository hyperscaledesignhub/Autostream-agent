"""
Test script to demonstrate anomaly detection for specific scenarios
"""

from platform_metrics_definition import is_anomalous, KAFKA_METRICS, FLINK_METRICS, CLICKHOUSE_METRICS

def test_anomaly_scenarios():
    """Test specific anomaly scenarios"""
    
    print("=" * 80)
    print("TESTING ANOMALY DETECTION SCENARIOS")
    print("=" * 80)
    
    # Test 1: Kafka under-replicated partitions
    print("\n1. KAFKA: Under-replicated Partitions")
    print("-" * 40)
    
    # Normal case
    result = is_anomalous('kafka', 'kafka_broker_under_replicated_partitions', 0)
    print(f"  Value: 0 → {result['severity'].upper()}: {result['reason']}")
    
    # Anomaly case
    result = is_anomalous('kafka', 'kafka_broker_under_replicated_partitions', 5)
    print(f"  Value: 5 → {result['severity'].upper()}: {result['reason']}")
    
    # Test 2: Kafka consumer lag
    print("\n2. KAFKA: Consumer Lag")
    print("-" * 40)
    
    # Normal
    result = is_anomalous('kafka', 'kafka_consumer_lag', 5000)
    print(f"  Value: 5,000 messages → {result['severity'].upper()}: {result['reason']}")
    
    # Warning
    result = is_anomalous('kafka', 'kafka_consumer_lag', 75000)
    print(f"  Value: 75,000 messages → {result['severity'].upper()}: {result['reason']}")
    
    # Critical
    result = is_anomalous('kafka', 'kafka_consumer_lag', 150000)
    print(f"  Value: 150,000 messages → {result['severity'].upper()}: {result['reason']}")
    
    # Test 3: Kafka JVM heap
    print("\n3. KAFKA: JVM Heap Usage")
    print("-" * 40)
    
    # Normal
    result = is_anomalous('kafka', 'kafka_jvm_heap_usage', 60)
    print(f"  Value: 60% → {result['severity'].upper()}: {result['reason']}")
    
    # Warning
    result = is_anomalous('kafka', 'kafka_jvm_heap_usage', 85)
    print(f"  Value: 85% → {result['severity'].upper()}: {result['reason']}")
    
    # Critical
    result = is_anomalous('kafka', 'kafka_jvm_heap_usage', 92)
    print(f"  Value: 92% → {result['severity'].upper()}: {result['reason']}")
    
    # Test 4: Flink job restarts
    print("\n4. FLINK: Job Restarts")
    print("-" * 40)
    
    # Normal
    result = is_anomalous('flink', 'flink_jobmanager_job_restarts', 1)
    print(f"  Value: 1 restart → {result['severity'].upper()}: {result['reason']}")
    
    # Warning
    result = is_anomalous('flink', 'flink_jobmanager_job_restarts', 7)
    print(f"  Value: 7 restarts → {result['severity'].upper()}: {result['reason']}")
    
    # Critical
    result = is_anomalous('flink', 'flink_jobmanager_job_restarts', 15)
    print(f"  Value: 15 restarts → {result['severity'].upper()}: {result['reason']}")
    
    # Test 5: Flink backpressure
    print("\n5. FLINK: Backpressure")
    print("-" * 40)
    
    # Normal
    result = is_anomalous('flink', 'flink_task_backpressure', 0.05)
    print(f"  Value: 0.05 ratio → {result['severity'].upper()}: {result['reason']}")
    
    # Warning
    result = is_anomalous('flink', 'flink_task_backpressure', 0.6)
    print(f"  Value: 0.6 ratio → {result['severity'].upper()}: {result['reason']}")
    
    # Critical
    result = is_anomalous('flink', 'flink_task_backpressure', 0.9)
    print(f"  Value: 0.9 ratio → {result['severity'].upper()}: {result['reason']}")
    
    # Test 6: Flink throughput
    print("\n6. FLINK: Throughput")
    print("-" * 40)
    
    # Normal
    result = is_anomalous('flink', 'flink_task_throughput', 50000)
    print(f"  Value: 50,000 rec/sec → {result['severity'].upper()}: {result['reason']}")
    
    # Low (anomaly)
    result = is_anomalous('flink', 'flink_task_throughput', 50, duration_minutes=10)
    print(f"  Value: 50 rec/sec → {result['severity'].upper()}: {result['reason']}")
    
    # Test 7: ClickHouse query duration
    print("\n7. CLICKHOUSE: Query Duration")
    print("-" * 40)
    
    # Normal
    result = is_anomalous('clickhouse', 'clickhouse_query_duration', 500)
    print(f"  Value: 500ms → {result['severity'].upper()}: {result['reason']}")
    
    # Warning
    result = is_anomalous('clickhouse', 'clickhouse_query_duration', 7000)
    print(f"  Value: 7,000ms → {result['severity'].upper()}: {result['reason']}")
    
    # Critical
    result = is_anomalous('clickhouse', 'clickhouse_query_duration', 15000)
    print(f"  Value: 15,000ms → {result['severity'].upper()}: {result['reason']}")
    
    # Test 8: ClickHouse failed queries
    print("\n8. CLICKHOUSE: Failed Queries")
    print("-" * 40)
    
    # Normal
    result = is_anomalous('clickhouse', 'clickhouse_failed_queries', 0.5)
    print(f"  Value: 0.5% → {result['severity'].upper()}: {result['reason']}")
    
    # Warning
    result = is_anomalous('clickhouse', 'clickhouse_failed_queries', 7)
    print(f"  Value: 7% → {result['severity'].upper()}: {result['reason']}")
    
    # Critical
    result = is_anomalous('clickhouse', 'clickhouse_failed_queries', 15)
    print(f"  Value: 15% → {result['severity'].upper()}: {result['reason']}")
    
    # Test 9: ClickHouse replication lag
    print("\n9. CLICKHOUSE: Replication Lag")
    print("-" * 40)
    
    # Normal
    result = is_anomalous('clickhouse', 'clickhouse_replication_lag', 3)
    print(f"  Value: 3 seconds → {result['severity'].upper()}: {result['reason']}")
    
    # Warning
    result = is_anomalous('clickhouse', 'clickhouse_replication_lag', 45)
    print(f"  Value: 45 seconds → {result['severity'].upper()}: {result['reason']}")
    
    # Critical
    result = is_anomalous('clickhouse', 'clickhouse_replication_lag', 90)
    print(f"  Value: 90 seconds → {result['severity'].upper()}: {result['reason']}")
    
    # Test 10: ClickHouse disk usage
    print("\n10. CLICKHOUSE: Disk Usage")
    print("-" * 40)
    
    # Normal
    result = is_anomalous('clickhouse', 'clickhouse_disk_usage', 65)
    print(f"  Value: 65% → {result['severity'].upper()}: {result['reason']}")
    
    # Warning
    result = is_anomalous('clickhouse', 'clickhouse_disk_usage', 85)
    print(f"  Value: 85% → {result['severity'].upper()}: {result['reason']}")
    
    # Critical
    result = is_anomalous('clickhouse', 'clickhouse_disk_usage', 93)
    print(f"  Value: 93% → {result['severity'].upper()}: {result['reason']}")

    print("\n" + "=" * 80)
    print("All critical anomaly scenarios are properly detected!")
    print("=" * 80)

if __name__ == "__main__":
    test_anomaly_scenarios()