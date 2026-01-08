# Streaming LLM Anomaly Detector

A Python application that generates dummy system metrics and uses OpenAI LLM to detect anomalies in real-time.

## Features

- **Dummy Metrics Generator**: Generates realistic system metrics (CPU, memory, latency, etc.)
- **OpenAI LLM Integration**: Uses GPT models to analyze metrics and detect anomalies
- **Real-time Streaming**: Continuously generates and analyzes metrics
- **Ground Truth Validation**: Randomly injects anomalies for testing

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure OpenAI API key:
```bash
cp .env.example .env
# Edit .env and add your OpenAI API key
```

3. Run the detector:
```bash
python main.py
```

## Usage

```bash
# Run with default settings (5-second intervals, 10 iterations)
python main.py

# Run continuously with 3-second intervals
python main.py --interval 3 --iterations 0

# Save results to file
python main.py --save-results results.json

# Use specific OpenAI model
python main.py --model gpt-4 --api-key YOUR_KEY
```

## How It Works

1. **Metrics Generation**: Generates 8 different system metrics with normal ranges
2. **Anomaly Injection**: Randomly injects anomalies (10% probability)
3. **LLM Analysis**: Sends metrics to OpenAI GPT with a specialized prompt
4. **Detection**: LLM determines if metrics show anomalies and explains findings

## Files

- `metrics_generator.py` - Generates dummy metrics with occasional anomalies
- `llm_anomaly_detector.py` - OpenAI LLM integration and anomaly detection
- `main.py` - Main application script
- `.env.example` - Environment configuration template
- `.gitignore` - Git ignore file to prevent committing secrets

## Requirements

- Python 3.7+
- OpenAI API key
- Dependencies listed in requirements.txt