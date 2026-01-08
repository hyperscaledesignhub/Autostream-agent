#!/usr/bin/env python3
import json
import time
import argparse
import os
from dotenv import load_dotenv
from metrics_generator import DummyMetricsGenerator
from llm_anomaly_detector import LLMAnomalyDetector

# Load environment variables from .env file
load_dotenv()

def print_separator():
    print("=" * 80)

def print_metrics(metrics_batch):
    print(f"\n📊 Generated Metrics at {metrics_batch['timestamp']}")
    print(f"   Host: {metrics_batch['metadata']['host']}")
    print(f"   Environment: {metrics_batch['metadata']['environment']}")
    print("\n   Current Values:")
    for name, data in metrics_batch['metrics'].items():
        value = data['value']
        expected = data['expected_range']
        unit = data['unit']
        print(f"   • {name:20}: {value:8.2f} {unit:10} (expected: {expected})")

def print_detection_result(result):
    detection = result['detection']
    
    if detection['anomaly_detected']:
        print(f"\n🚨 ANOMALY DETECTED!")
    else:
        print(f"\n✅ Normal Operation")
    
    print(f"   Confidence: {detection['confidence']}%")
    print(f"   Detection Method: {detection['detection_method']}")
    
    if detection['anomaly_detected'] and detection['anomalous_metrics']:
        print(f"   Anomalous Metrics: {', '.join(detection['anomalous_metrics'])}")
    
    print(f"   Explanation: {detection['explanation']}")

def main():
    parser = argparse.ArgumentParser(description='Streaming LLM Anomaly Detector')
    parser.add_argument('--interval', type=int, default=5, 
                       help='Interval between metric generations (seconds)')
    parser.add_argument('--iterations', type=int, default=10,
                       help='Number of iterations to run (0 for infinite)')
    parser.add_argument('--api-key', type=str, help='OpenAI API key (overrides environment variable)')
    parser.add_argument('--model', type=str, default='gpt-3.5-turbo',
                       help='OpenAI model to use')
    parser.add_argument('--save-results', type=str, 
                       help='Save results to JSON file')
    
    args = parser.parse_args()
    
    print("🚀 Starting Streaming LLM Anomaly Detector")
    print_separator()
    
    # Initialize components
    generator = DummyMetricsGenerator()
    
    try:
        detector = LLMAnomalyDetector(api_key=args.api_key, model=args.model)
        print(f"✓ Using OpenAI model: {args.model}")
    except ValueError as e:
        print(f"❌ Error: {e}")
        print("\nTo fix this:")
        print("1. Create a .env file from .env.example")
        print("2. Add your OpenAI API key to the .env file")
        print("3. Or pass the API key using --api-key flag")
        return
    
    print_separator()
    
    results = []
    iteration = 0
    
    try:
        for metrics_batch in generator.stream_metrics(args.interval):
            iteration += 1
            
            # Display generated metrics
            print_metrics(metrics_batch)
            
            # Analyze with LLM
            print("\n🔍 Analyzing with OpenAI LLM...")
            analysis_result = detector.analyze_stream(metrics_batch)
            
            # Display detection results
            print_detection_result(analysis_result)
            
            # Store results if needed
            if args.save_results:
                results.append(analysis_result)
            
            # Ground truth (if available from generator)
            if metrics_batch['metadata'].get('injected_anomaly'):
                print(f"\n   📌 Ground Truth: Anomaly was injected in "
                     f"{', '.join(metrics_batch['metadata']['anomaly_metrics'])}")
            
            print_separator()
            
            # Check iteration limit
            if args.iterations > 0 and iteration >= args.iterations:
                break
                
    except KeyboardInterrupt:
        print("\n\n🛑 Stopped by user")
    
    # Save results if requested
    if args.save_results and results:
        with open(args.save_results, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n💾 Results saved to {args.save_results}")
    
    print(f"\n📈 Summary: Processed {iteration} metric batches")
    if results:
        anomalies = sum(1 for r in results if r['detection']['anomaly_detected'])
        print(f"   Anomalies detected: {anomalies}/{iteration} ({100*anomalies/iteration:.1f}%)")

if __name__ == "__main__":
    main()