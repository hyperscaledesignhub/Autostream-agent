"""
Test System with SQLite Database (no Docker required)
Quick test of the monitoring system without TimescaleDB
"""

import sqlite3
import threading
import time
import json
from datetime import datetime, timedelta
from platform_metrics_generator import PlatformMetricsGenerator

class SQLiteTestDB:
    def __init__(self, db_path="test_metrics.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize SQLite database with simplified schema"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        # Create tables
        cur.execute("""
            CREATE TABLE IF NOT EXISTS platform_metrics (
                time TEXT NOT NULL,
                component TEXT NOT NULL,
                metric_name TEXT NOT NULL,
                value REAL NOT NULL,
                unit TEXT,
                host TEXT DEFAULT 'test-host',
                environment TEXT DEFAULT 'test'
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS anomaly_events (
                time TEXT NOT NULL,
                component TEXT NOT NULL,
                metric_name TEXT NOT NULL,
                value REAL NOT NULL,
                severity TEXT NOT NULL,
                reason TEXT
            )
        """)
        
        # Create indexes
        cur.execute("CREATE INDEX IF NOT EXISTS idx_metrics_time ON platform_metrics(time)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_anomalies_time ON anomaly_events(time)")
        
        conn.commit()
        conn.close()
        print("✅ SQLite test database initialized")
    
    def insert_metrics(self, metrics_batch):
        """Insert metrics batch into SQLite"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        try:
            for component in ['kafka', 'flink', 'clickhouse']:
                if component in metrics_batch['metrics']:
                    for metric_name, value in metrics_batch['metrics'][component].items():
                        cur.execute("""
                            INSERT INTO platform_metrics 
                            (time, component, metric_name, value, unit, host, environment)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (
                            metrics_batch['timestamp'],
                            component,
                            metric_name,
                            value,
                            None,  # unit
                            'test-server-01',
                            'test'
                        ))
            
            # Insert anomalies if any were detected
            if metrics_batch['metadata'].get('detected_anomalies'):
                for component, anomalies in metrics_batch['metadata']['detected_anomalies'].items():
                    for anomaly in anomalies:
                        cur.execute("""
                            INSERT INTO anomaly_events 
                            (time, component, metric_name, value, severity, reason)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            metrics_batch['timestamp'],
                            component,
                            anomaly['metric'],
                            anomaly['value'],
                            anomaly['severity'],
                            anomaly['reason']
                        ))
            
            conn.commit()
            return True
            
        except Exception as e:
            print(f"❌ Error inserting data: {e}")
            return False
        finally:
            conn.close()
    
    def get_stats(self):
        """Get database statistics"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        # Total metrics
        cur.execute("SELECT COUNT(*) FROM platform_metrics")
        total_metrics = cur.fetchone()[0]
        
        # Recent metrics (last 2 minutes)
        recent_time = datetime.now() - timedelta(minutes=2)
        cur.execute("""
            SELECT COUNT(*) FROM platform_metrics 
            WHERE time > ?
        """, (recent_time.isoformat(),))
        recent_metrics = cur.fetchone()[0]
        
        # Total anomalies
        cur.execute("SELECT COUNT(*) FROM anomaly_events")
        total_anomalies = cur.fetchone()[0]
        
        # Recent anomalies
        cur.execute("""
            SELECT COUNT(*) FROM anomaly_events 
            WHERE time > ?
        """, (recent_time.isoformat(),))
        recent_anomalies = cur.fetchone()[0]
        
        # Component breakdown
        cur.execute("""
            SELECT component, COUNT(*) 
            FROM platform_metrics 
            WHERE time > ?
            GROUP BY component
        """, (recent_time.isoformat(),))
        component_stats = cur.fetchall()
        
        conn.close()
        
        return {
            'total_metrics': total_metrics,
            'recent_metrics': recent_metrics,
            'total_anomalies': total_anomalies,
            'recent_anomalies': recent_anomalies,
            'component_stats': dict(component_stats)
        }

class TestDataIngestor:
    def __init__(self, interval_seconds=10):
        self.interval_seconds = interval_seconds
        self.running = False
        self.db = SQLiteTestDB()
        self.generator = PlatformMetricsGenerator(anomaly_probability=0.2)
        self.batch_count = 0
    
    def start_ingestion(self):
        """Start data ingestion loop"""
        self.running = True
        
        def ingestion_loop():
            print(f"🚀 Starting test data ingestion (interval: {self.interval_seconds}s)")
            
            while self.running:
                try:
                    # Generate metrics
                    batch = self.generator.generate_metrics_batch()
                    
                    # Insert into database
                    success = self.db.insert_metrics(batch)
                    
                    if success:
                        self.batch_count += 1
                        
                        # Print status
                        if batch['metadata'].get('injected_anomaly'):
                            anomaly_info = batch['metadata']['injected_anomaly']
                            print(f"⚠️  [{datetime.now().strftime('%H:%M:%S')}] Injected {anomaly_info['severity']} anomaly: {anomaly_info['description']}")
                        else:
                            if self.batch_count % 6 == 0:  # Every minute
                                stats = self.db.get_stats()
                                print(f"📊 [{datetime.now().strftime('%H:%M:%S')}] Stats: {stats['recent_metrics']} metrics, {stats['recent_anomalies']} anomalies (last 2min)")
                    
                    time.sleep(self.interval_seconds)
                    
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    print(f"❌ Error in ingestion: {e}")
                    time.sleep(self.interval_seconds)
        
        # Start in background thread
        thread = threading.Thread(target=ingestion_loop)
        thread.daemon = True
        thread.start()
        
        return thread
    
    def stop(self):
        """Stop ingestion"""
        self.running = False
        print(f"🛑 Stopped ingestion after {self.batch_count} batches")

def test_monitoring_system():
    """Test the monitoring system with SQLite"""
    print("🧪 Testing Platform Monitoring System (SQLite)")
    print("=" * 60)
    
    # Create test ingestor
    ingestor = TestDataIngestor(interval_seconds=5)
    
    # Start ingestion
    thread = ingestor.start_ingestion()
    
    print("✅ Test system started")
    print("📡 Data ingestion running (5-second intervals)")
    print("🔍 Monitoring for anomalies...")
    print("\nPress Ctrl+C to stop and show final stats")
    print("=" * 60)
    
    try:
        # Let it run for a bit
        while thread.is_alive():
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping test system...")
        ingestor.stop()
        thread.join(timeout=2)
        
        # Show final stats
        print("\n📊 Final Statistics:")
        print("=" * 30)
        stats = ingestor.db.get_stats()
        
        print(f"Total Metrics Ingested: {stats['total_metrics']:,}")
        print(f"Total Anomalies Detected: {stats['total_anomalies']}")
        print(f"Batches Processed: {ingestor.batch_count}")
        print(f"Recent Activity (2min): {stats['recent_metrics']} metrics, {stats['recent_anomalies']} anomalies")
        
        if stats['component_stats']:
            print(f"\nComponent Breakdown (recent):")
            for component, count in stats['component_stats'].items():
                print(f"  {component}: {count} metrics")
        
        # Show sample data
        print(f"\n📋 Sample Data Query:")
        conn = sqlite3.connect(ingestor.db.db_path)
        cur = conn.cursor()
        
        # Recent metrics
        cur.execute("""
            SELECT component, metric_name, value, time 
            FROM platform_metrics 
            ORDER BY time DESC 
            LIMIT 5
        """)
        recent_metrics = cur.fetchall()
        
        print("Recent Metrics:")
        for metric in recent_metrics:
            print(f"  {metric[0]}/{metric[1]}: {metric[2]} at {metric[3]}")
        
        # Recent anomalies
        cur.execute("""
            SELECT component, metric_name, value, severity, reason 
            FROM anomaly_events 
            ORDER BY time DESC 
            LIMIT 3
        """)
        recent_anomalies = cur.fetchall()
        
        if recent_anomalies:
            print("\nRecent Anomalies:")
            for anomaly in recent_anomalies:
                print(f"  {anomaly[0]}/{anomaly[1]}: {anomaly[2]} ({anomaly[3]}) - {anomaly[4]}")
        
        conn.close()
        
        print(f"\n✅ Test database saved as: {ingestor.db.db_path}")
        print("You can inspect it with any SQLite browser")

if __name__ == "__main__":
    test_monitoring_system()