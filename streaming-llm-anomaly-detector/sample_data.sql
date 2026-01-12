-- Sample initial data for testing
-- This will be loaded after schema creation

-- Insert some initial sample metrics for the last hour
DO $$
DECLARE
    i INTEGER;
    current_time TIMESTAMPTZ;
    base_time TIMESTAMPTZ;
BEGIN
    -- Set base time to 1 hour ago
    base_time := NOW() - INTERVAL '1 hour';
    
    -- Insert sample metrics for the last hour (every 30 seconds)
    FOR i IN 0..119 LOOP
        current_time := base_time + (i * INTERVAL '30 seconds');
        
        -- Kafka metrics
        INSERT INTO platform_metrics (time, component, metric_name, value, unit, host, cluster, environment)
        VALUES 
            (current_time, 'kafka', 'kafka_broker_under_replicated_partitions', 0, 'count', 'kafka-broker-01', 'main-cluster', 'production'),
            (current_time, 'kafka', 'kafka_consumer_lag', 5000 + (random() * 10000)::INTEGER, 'messages', 'kafka-broker-01', 'main-cluster', 'production'),
            (current_time, 'kafka', 'kafka_jvm_heap_usage', 40 + (random() * 30)::NUMERIC, '%', 'kafka-broker-01', 'main-cluster', 'production'),
            (current_time, 'kafka', 'kafka_broker_messages_in_per_sec', 10000 + (random() * 20000)::INTEGER, 'msg/sec', 'kafka-broker-01', 'main-cluster', 'production');
        
        -- Flink metrics
        INSERT INTO platform_metrics (time, component, metric_name, value, unit, host, cluster, environment)
        VALUES 
            (current_time, 'flink', 'flink_jobmanager_job_restarts', (random() * 3)::INTEGER, 'count', 'flink-jobmanager-01', 'main-cluster', 'production'),
            (current_time, 'flink', 'flink_task_backpressure', random() * 0.3, 'ratio', 'flink-taskmanager-01', 'main-cluster', 'production'),
            (current_time, 'flink', 'flink_task_throughput', 50000 + (random() * 40000)::INTEGER, 'records/sec', 'flink-taskmanager-01', 'main-cluster', 'production'),
            (current_time, 'flink', 'flink_taskmanager_heap_used', 30 + (random() * 40)::NUMERIC, '%', 'flink-taskmanager-01', 'main-cluster', 'production');
        
        -- ClickHouse metrics
        INSERT INTO platform_metrics (time, component, metric_name, value, unit, host, cluster, environment)
        VALUES 
            (current_time, 'clickhouse', 'clickhouse_query_duration', 100 + (random() * 500)::INTEGER, 'ms', 'clickhouse-01', 'main-cluster', 'production'),
            (current_time, 'clickhouse', 'clickhouse_failed_queries', random() * 2, '%', 'clickhouse-01', 'main-cluster', 'production'),
            (current_time, 'clickhouse', 'clickhouse_disk_usage', 50 + (random() * 20)::NUMERIC, '%', 'clickhouse-01', 'main-cluster', 'production'),
            (current_time, 'clickhouse', 'clickhouse_replication_lag', (random() * 10)::INTEGER, 'seconds', 'clickhouse-01', 'main-cluster', 'production');
    END LOOP;
    
    RAISE NOTICE 'Inserted % sample metric records for the last hour', (120 * 12);
END $$;

-- Insert a few sample anomalies for testing
INSERT INTO anomaly_events (time, component, metric_name, value, severity, reason)
VALUES 
    (NOW() - INTERVAL '30 minutes', 'kafka', 'kafka_consumer_lag', 150000, 'critical', 'Consumer lag exceeds 100k messages'),
    (NOW() - INTERVAL '25 minutes', 'flink', 'flink_jobmanager_job_restarts', 8, 'warning', 'Multiple job restarts detected'),
    (NOW() - INTERVAL '20 minutes', 'clickhouse', 'clickhouse_query_duration', 12000, 'critical', 'Query duration exceeds 10 seconds'),
    (NOW() - INTERVAL '15 minutes', 'kafka', 'kafka_jvm_heap_usage', 88, 'warning', 'JVM heap usage above 80%');

-- Resolve some older anomalies
UPDATE anomaly_events 
SET resolved_at = time + INTERVAL '10 minutes' 
WHERE time < NOW() - INTERVAL '10 minutes';

-- Refresh the continuous aggregates to include our sample data
CALL refresh_continuous_aggregate('metrics_1min', NOW() - INTERVAL '2 hours', NOW());
CALL refresh_continuous_aggregate('metrics_5min', NOW() - INTERVAL '2 hours', NOW());
CALL refresh_continuous_aggregate('metrics_1hour', NOW() - INTERVAL '2 hours', NOW());
CALL refresh_continuous_aggregate('anomaly_summary_1hour', NOW() - INTERVAL '2 hours', NOW());

-- Display initial statistics
SELECT 'Platform Metrics Count' as table_name, COUNT(*) as count FROM platform_metrics
UNION ALL
SELECT 'Anomaly Events Count', COUNT(*) FROM anomaly_events
UNION ALL
SELECT 'Active Anomalies', COUNT(*) FROM anomaly_events WHERE resolved_at IS NULL;