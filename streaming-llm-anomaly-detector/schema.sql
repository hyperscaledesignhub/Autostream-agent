-- Platform Metrics Database Schema for TimescaleDB
-- Creates tables, hypertables, and initial setup

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- Main metrics table
CREATE TABLE platform_metrics (
    time            TIMESTAMPTZ NOT NULL,
    component       VARCHAR(20) NOT NULL,  -- 'kafka', 'flink', 'clickhouse'
    metric_name     VARCHAR(100) NOT NULL,
    value           DOUBLE PRECISION NOT NULL,
    unit            VARCHAR(20),
    host            VARCHAR(100),
    cluster         VARCHAR(50) DEFAULT 'main-cluster',
    environment     VARCHAR(20) DEFAULT 'production',
    tags            JSONB
);

-- Convert to hypertable for time-series optimization
SELECT create_hypertable('platform_metrics', 'time');

-- Create indexes for common queries
CREATE INDEX idx_component_metric ON platform_metrics (component, metric_name, time DESC);
CREATE INDEX idx_host_time ON platform_metrics (host, time DESC);
CREATE INDEX idx_environment_time ON platform_metrics (environment, time DESC);
CREATE INDEX idx_time_component ON platform_metrics (time, component);

-- Anomaly detection results table
CREATE TABLE anomaly_events (
    time            TIMESTAMPTZ NOT NULL,
    component       VARCHAR(20) NOT NULL,
    metric_name     VARCHAR(100) NOT NULL,
    value           DOUBLE PRECISION NOT NULL,
    severity        VARCHAR(20) NOT NULL,  -- 'warning', 'critical'
    threshold       DOUBLE PRECISION,
    reason          TEXT,
    duration_minutes INTEGER DEFAULT 0,
    resolved_at     TIMESTAMPTZ,
    tags            JSONB
);

-- Convert to hypertable
SELECT create_hypertable('anomaly_events', 'time');

-- Create index for active anomalies
CREATE INDEX idx_active_anomalies ON anomaly_events (resolved_at, time DESC) 
WHERE resolved_at IS NULL;

CREATE INDEX idx_component_severity ON anomaly_events (component, severity, time DESC);
CREATE INDEX idx_time_severity ON anomaly_events (time, severity);

-- Continuous aggregates for 1-minute averages
CREATE MATERIALIZED VIEW metrics_1min
WITH (timescaledb.continuous) AS
SELECT 
    time_bucket('1 minute', time) AS bucket,
    component,
    metric_name,
    AVG(value) as avg_value,
    MIN(value) as min_value,
    MAX(value) as max_value,
    COUNT(*) as sample_count
FROM platform_metrics
GROUP BY bucket, component, metric_name
WITH NO DATA;

-- Continuous aggregates for 5-minute averages (for cross-component analysis)
CREATE MATERIALIZED VIEW metrics_5min
WITH (timescaledb.continuous) AS
SELECT 
    time_bucket('5 minutes', time) AS bucket,
    component,
    metric_name,
    AVG(value) as avg_value,
    MIN(value) as min_value,
    MAX(value) as max_value,
    STDDEV(value) as stddev_value,
    COUNT(*) as sample_count
FROM platform_metrics
GROUP BY bucket, component, metric_name
WITH NO DATA;

-- Continuous aggregates for hourly summaries
CREATE MATERIALIZED VIEW metrics_1hour
WITH (timescaledb.continuous) AS
SELECT 
    time_bucket('1 hour', time) AS bucket,
    component,
    AVG(value) as avg_value,
    MIN(value) as min_value,
    MAX(value) as max_value,
    COUNT(DISTINCT metric_name) as unique_metrics,
    COUNT(*) as total_samples
FROM platform_metrics
GROUP BY bucket, component
WITH NO DATA;

-- Anomaly summary view
CREATE MATERIALIZED VIEW anomaly_summary_1hour
WITH (timescaledb.continuous) AS
SELECT 
    time_bucket('1 hour', time) AS bucket,
    component,
    severity,
    COUNT(*) as anomaly_count,
    COUNT(DISTINCT metric_name) as affected_metrics,
    AVG(EXTRACT(EPOCH FROM (COALESCE(resolved_at, NOW()) - time))/60)::INTEGER as avg_duration_minutes
FROM anomaly_events
GROUP BY bucket, component, severity
WITH NO DATA;

-- Retention policies (optional - keep 30 days of raw data)
SELECT add_retention_policy('platform_metrics', INTERVAL '30 days');
SELECT add_retention_policy('anomaly_events', INTERVAL '90 days');

-- Refresh policies for continuous aggregates
SELECT add_continuous_aggregate_policy('metrics_1min',
    start_offset => INTERVAL '1 hour',
    end_offset => INTERVAL '1 minute',
    schedule_interval => INTERVAL '1 minute');

SELECT add_continuous_aggregate_policy('metrics_5min',
    start_offset => INTERVAL '2 hours',
    end_offset => INTERVAL '5 minutes',
    schedule_interval => INTERVAL '5 minutes');

SELECT add_continuous_aggregate_policy('metrics_1hour',
    start_offset => INTERVAL '24 hours',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour');

SELECT add_continuous_aggregate_policy('anomaly_summary_1hour',
    start_offset => INTERVAL '24 hours',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour');

-- Create function to automatically detect and insert anomalies
CREATE OR REPLACE FUNCTION detect_and_insert_anomaly()
RETURNS TRIGGER AS $$
DECLARE
    metric_definition RECORD;
    is_anomaly BOOLEAN := FALSE;
    anomaly_severity VARCHAR(20) := 'normal';
    anomaly_reason TEXT := 'Within normal range';
BEGIN
    -- Simple anomaly detection logic
    -- In production, this would use more sophisticated detection
    
    -- Kafka metrics anomaly detection
    IF NEW.component = 'kafka' THEN
        IF NEW.metric_name = 'kafka_broker_under_replicated_partitions' AND NEW.value > 0 THEN
            is_anomaly := TRUE;
            anomaly_severity := 'critical';
            anomaly_reason := 'Under-replicated partitions detected';
        ELSIF NEW.metric_name = 'kafka_consumer_lag' AND NEW.value > 100000 THEN
            is_anomaly := TRUE;
            anomaly_severity := 'critical';
            anomaly_reason := 'Consumer lag exceeds 100k messages';
        ELSIF NEW.metric_name = 'kafka_consumer_lag' AND NEW.value > 50000 THEN
            is_anomaly := TRUE;
            anomaly_severity := 'warning';
            anomaly_reason := 'Consumer lag exceeds 50k messages';
        ELSIF NEW.metric_name = 'kafka_jvm_heap_usage' AND NEW.value > 90 THEN
            is_anomaly := TRUE;
            anomaly_severity := 'critical';
            anomaly_reason := 'JVM heap usage above 90%';
        ELSIF NEW.metric_name = 'kafka_jvm_heap_usage' AND NEW.value > 80 THEN
            is_anomaly := TRUE;
            anomaly_severity := 'warning';
            anomaly_reason := 'JVM heap usage above 80%';
        END IF;
    END IF;
    
    -- Flink metrics anomaly detection
    IF NEW.component = 'flink' THEN
        IF NEW.metric_name = 'flink_jobmanager_job_restarts' AND NEW.value > 10 THEN
            is_anomaly := TRUE;
            anomaly_severity := 'critical';
            anomaly_reason := 'Excessive job restarts detected';
        ELSIF NEW.metric_name = 'flink_jobmanager_job_restarts' AND NEW.value > 5 THEN
            is_anomaly := TRUE;
            anomaly_severity := 'warning';
            anomaly_reason := 'Multiple job restarts detected';
        ELSIF NEW.metric_name = 'flink_task_backpressure' AND NEW.value > 0.8 THEN
            is_anomaly := TRUE;
            anomaly_severity := 'critical';
            anomaly_reason := 'High backpressure detected';
        ELSIF NEW.metric_name = 'flink_task_backpressure' AND NEW.value > 0.5 THEN
            is_anomaly := TRUE;
            anomaly_severity := 'warning';
            anomaly_reason := 'Backpressure detected';
        ELSIF NEW.metric_name = 'flink_task_throughput' AND NEW.value < 100 THEN
            is_anomaly := TRUE;
            anomaly_severity := 'warning';
            anomaly_reason := 'Very low throughput detected';
        END IF;
    END IF;
    
    -- ClickHouse metrics anomaly detection
    IF NEW.component = 'clickhouse' THEN
        IF NEW.metric_name = 'clickhouse_query_duration' AND NEW.value > 10000 THEN
            is_anomaly := TRUE;
            anomaly_severity := 'critical';
            anomaly_reason := 'Query duration exceeds 10 seconds';
        ELSIF NEW.metric_name = 'clickhouse_query_duration' AND NEW.value > 5000 THEN
            is_anomaly := TRUE;
            anomaly_severity := 'warning';
            anomaly_reason := 'Query duration exceeds 5 seconds';
        ELSIF NEW.metric_name = 'clickhouse_failed_queries' AND NEW.value > 10 THEN
            is_anomaly := TRUE;
            anomaly_severity := 'critical';
            anomaly_reason := 'Failed query rate above 10%';
        ELSIF NEW.metric_name = 'clickhouse_disk_usage' AND NEW.value > 90 THEN
            is_anomaly := TRUE;
            anomaly_severity := 'critical';
            anomaly_reason := 'Disk usage above 90%';
        ELSIF NEW.metric_name = 'clickhouse_disk_usage' AND NEW.value > 80 THEN
            is_anomaly := TRUE;
            anomaly_severity := 'warning';
            anomaly_reason := 'Disk usage above 80%';
        END IF;
    END IF;
    
    -- Insert anomaly if detected
    IF is_anomaly THEN
        INSERT INTO anomaly_events (
            time, component, metric_name, value, severity, reason
        ) VALUES (
            NEW.time, NEW.component, NEW.metric_name, NEW.value, anomaly_severity, anomaly_reason
        );
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to automatically detect anomalies on metric inserts
CREATE TRIGGER anomaly_detection_trigger
    AFTER INSERT ON platform_metrics
    FOR EACH ROW
    EXECUTE FUNCTION detect_and_insert_anomaly();

-- Create some helper views
CREATE VIEW current_system_health AS
SELECT 
    component,
    COUNT(CASE WHEN severity = 'critical' THEN 1 END) as critical_anomalies,
    COUNT(CASE WHEN severity = 'warning' THEN 1 END) as warning_anomalies,
    COUNT(*) as total_anomalies,
    MAX(time) as last_anomaly
FROM anomaly_events
WHERE time >= NOW() - INTERVAL '5 minutes'
AND resolved_at IS NULL
GROUP BY component;

CREATE VIEW recent_metrics_summary AS
SELECT 
    component,
    metric_name,
    AVG(value) as avg_value,
    MIN(value) as min_value,
    MAX(value) as max_value,
    COUNT(*) as sample_count,
    MAX(time) as last_update
FROM platform_metrics
WHERE time >= NOW() - INTERVAL '10 minutes'
GROUP BY component, metric_name
ORDER BY component, metric_name;

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;