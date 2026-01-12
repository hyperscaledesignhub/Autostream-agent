"""
Data Ingestor Service
Continuously generates and ingests platform metrics into TimescaleDB every 10 seconds
"""

import time
import threading
import signal
import sys
from datetime import datetime
from typing import Dict, List
import psycopg2
from psycopg2.extras import RealDictCursor
import json
import random

from platform_metrics_generator import PlatformMetricsGenerator
from platform_metrics_definition import is_anomalous

# Database connection configuration
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'metrics_db',
    'user': 'postgres',
    'password': 'password'
}

class DataIngestorService:
    def __init__(self, interval_seconds: int = 10):
        self.interval_seconds = interval_seconds
        self.running = False
        self.metrics_generator = PlatformMetricsGenerator(anomaly_probability=0.15)
        self.ingestion_count = 0
        self.anomaly_count = 0
        
    def get_db_connection(self):
        """Create a database connection"""
        try:
            return psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            return None
    
    def wait_for_database(self, max_retries: int = 30):
        """Wait for database to be ready"""
        print("⏳ Waiting for TimescaleDB to be ready...")
        
        for attempt in range(max_retries):
            try:
                conn = self.get_db_connection()
                if conn:
                    cur = conn.cursor()
                    cur.execute("SELECT 1")
                    cur.close()
                    conn.close()
                    print("✅ Database is ready!")
                    return True
            except Exception:
                print(f"   Attempt {attempt + 1}/{max_retries} - Database not ready yet...")
                time.sleep(2)
        
        print("❌ Database failed to become ready")
        return False
    
    def insert_metrics_batch(self, metrics_batch: Dict):
        """Insert a batch of metrics into the database"""
        conn = self.get_db_connection()
        if not conn:
            return False
        
        try:
            cur = conn.cursor()
            
            # Insert metrics
            for component in ['kafka', 'flink', 'clickhouse']:
                if component in metrics_batch['metrics']:
                    for metric_name, metric_data in metrics_batch['metrics'][component].items():
                        # Insert metric
                        insert_query = """
                        INSERT INTO platform_metrics 
                        (time, component, metric_name, value, unit, host, cluster, environment, tags)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """
                        
                        # Get unit from metric definition if available
                        unit = None
                        if isinstance(metric_data, dict) and 'unit' in metric_data:
                            unit = metric_data['unit']
                            value = metric_data['value']
                        else:
                            value = metric_data
                        
                        cur.execute(insert_query, (
                            metrics_batch['timestamp'],
                            component,
                            metric_name,
                            value,
                            unit,
                            metrics_batch['metadata'].get('cluster', 'server-01'),
                            metrics_batch['metadata'].get('cluster', 'main-cluster'),
                            metrics_batch['metadata'].get('environment', 'production'),
                            json.dumps(metrics_batch['metadata'])
                        ))
            
            # Commit the transaction
            conn.commit()
            cur.close()
            conn.close()
            
            self.ingestion_count += 1
            return True
            
        except Exception as e:
            print(f"❌ Error inserting metrics: {e}")
            if conn:
                conn.rollback()
                conn.close()
            return False
    
    def check_and_resolve_old_anomalies(self):
        """Check and resolve anomalies that might have been resolved"""
        conn = self.get_db_connection()
        if not conn:
            return
        
        try:
            cur = conn.cursor()
            
            # Resolve anomalies that are older than 5 minutes and haven't been resolved
            # This is a simple resolution strategy - in practice, you'd have more sophisticated logic
            resolve_query = """
            UPDATE anomaly_events 
            SET resolved_at = NOW()
            WHERE resolved_at IS NULL 
            AND time < NOW() - INTERVAL '5 minutes'
            AND severity = 'warning'
            """
            
            cur.execute(resolve_query)
            
            # Resolve critical anomalies after 10 minutes (assuming they've been addressed)
            resolve_critical_query = """
            UPDATE anomaly_events 
            SET resolved_at = NOW()
            WHERE resolved_at IS NULL 
            AND time < NOW() - INTERVAL '10 minutes'
            AND severity = 'critical'
            """
            
            cur.execute(resolve_critical_query)
            
            conn.commit()
            cur.close()
            conn.close()
            
        except Exception as e:
            print(f"❌ Error resolving old anomalies: {e}")
            if conn:
                conn.rollback()
                conn.close()
    
    def print_ingestion_stats(self):
        """Print current ingestion statistics"""
        conn = self.get_db_connection()
        if not conn:
            return
        
        try:
            cur = conn.cursor()
            
            # Get total metrics count
            cur.execute("SELECT COUNT(*) FROM platform_metrics")
            total_metrics = cur.fetchone()[0]
            
            # Get active anomalies
            cur.execute("""
                SELECT component, severity, COUNT(*) as count
                FROM anomaly_events 
                WHERE resolved_at IS NULL 
                GROUP BY component, severity
                ORDER BY component, severity DESC
            """)
            active_anomalies = cur.fetchall()
            
            # Get recent metrics count
            cur.execute("""
                SELECT COUNT(*) FROM platform_metrics 
                WHERE time >= NOW() - INTERVAL '1 minute'
            """)
            recent_metrics = cur.fetchone()[0]
            
            cur.close()
            conn.close()
            
            print(f"\n📊 Ingestion Stats [{datetime.now().strftime('%H:%M:%S')}]:")
            print(f"   Total Metrics Ingested: {total_metrics:,}")
            print(f"   Recent (1 min): {recent_metrics}")
            print(f"   Batches Processed: {self.ingestion_count}")
            
            if active_anomalies:
                print(f"   🚨 Active Anomalies:")
                for anomaly in active_anomalies:
                    print(f"      {anomaly['component']}: {anomaly['count']} {anomaly['severity']}")
            else:
                print(f"   ✅ No active anomalies")
            
        except Exception as e:
            print(f"❌ Error getting stats: {e}")
    
    def ingestion_loop(self):
        """Main ingestion loop"""
        print(f"🚀 Starting data ingestion (interval: {self.interval_seconds}s)")
        
        while self.running:
            try:
                # Generate metrics batch
                metrics_batch = self.metrics_generator.generate_metrics_batch()
                
                # Insert into database
                success = self.insert_metrics_batch(metrics_batch)
                
                if success:
                    # Check if anomalies were injected
                    if metrics_batch['metadata'].get('injected_anomaly'):
                        anomaly_info = metrics_batch['metadata']['injected_anomaly']
                        print(f"⚠️  Injected {anomaly_info['severity']} anomaly: {anomaly_info['description']}")
                        self.anomaly_count += 1
                else:
                    print("❌ Failed to insert metrics batch")
                
                # Resolve old anomalies periodically
                if self.ingestion_count % 6 == 0:  # Every ~1 minute
                    self.check_and_resolve_old_anomalies()
                
                # Print stats periodically
                if self.ingestion_count % 12 == 0:  # Every ~2 minutes
                    self.print_ingestion_stats()
                
                # Wait for next interval
                time.sleep(self.interval_seconds)
                
            except KeyboardInterrupt:
                print("\n🛑 Received shutdown signal")
                break
            except Exception as e:
                print(f"❌ Error in ingestion loop: {e}")
                time.sleep(self.interval_seconds)
    
    def start(self):
        """Start the ingestion service"""
        # Wait for database to be ready
        if not self.wait_for_database():
            print("❌ Cannot start ingestion service - database not available")
            return False
        
        self.running = True
        
        # Start ingestion in a separate thread
        self.ingestion_thread = threading.Thread(target=self.ingestion_loop)
        self.ingestion_thread.daemon = True
        self.ingestion_thread.start()
        
        print("✅ Data ingestion service started")
        return True
    
    def stop(self):
        """Stop the ingestion service"""
        print("🛑 Stopping data ingestion service...")
        self.running = False
        if hasattr(self, 'ingestion_thread'):
            self.ingestion_thread.join(timeout=5)
        print(f"✅ Service stopped. Processed {self.ingestion_count} batches")

def signal_handler(sig, frame):
    """Handle shutdown signals"""
    print(f"\n🛑 Received signal {sig}")
    if 'ingestor' in globals():
        ingestor.stop()
    sys.exit(0)

def main():
    """Main function"""
    global ingestor
    
    print("🚀 Platform Metrics Data Ingestor")
    print("=" * 50)
    
    # Setup signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create and start ingestor
    ingestor = DataIngestorService(interval_seconds=10)
    
    if not ingestor.start():
        sys.exit(1)
    
    print("\n📡 Data ingestion running...")
    print("   Press Ctrl+C to stop")
    print("=" * 50)
    
    try:
        # Keep the main thread alive
        while ingestor.running:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        ingestor.stop()

if __name__ == "__main__":
    main()