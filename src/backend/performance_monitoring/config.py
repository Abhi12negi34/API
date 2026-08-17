import logging
from flask import Flask, request, jsonify

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# In-memory storage for performance thresholds (replace with database in production)
performance_thresholds = {}

def validate_latency_threshold(endpoint, p95_latency_ms):
    """Validates the latency threshold to prevent unreasonable values."""
    if not isinstance(p95_latency_ms, (int, float)):
        raise ValueError("Latency must be a number.")
    if p95_latency_ms <= 0:
        raise ValueError("Latency must be greater than zero.")
    if p95_latency_ms > 10000:  # Example maximum latency (adjust as needed)
        raise ValueError("Latency is unreasonably high.")
    return True

@app.route('/api-monitoring/metrics', methods=['GET'])
def get_metric():
    """Retrieves the p95 latency for a given endpoint."""
    endpoint = request.args.get('endpoint')

    if not endpoint:
        logger.error("Endpoint parameter is missing.")
        return jsonify({"error": "Endpoint parameter is required"}), 400

    try:
        # Simulate retrieving metrics from the monitoring system (replace with actual integration)
        p95_latency = performance_thresholds.get(endpoint, {}).get('p95_latency_ms')

        if p95_latency is None:
            logger.warning(f"No monitoring data found for endpoint: {endpoint}")
            return jsonify({"error": "No monitoring data available"}), 404

        return jsonify({'p95_latency': p95_latency}), 200

    except Exception as e:
        logger.error(f"Error retrieving metrics for endpoint {endpoint}: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/config/thresholds', methods=['POST'])
def configure_threshold():
    """Configures performance thresholds for an endpoint."""
    try:
        data = request.get_json()
        endpoint = data.get('endpoint')
        p95_latency_ms = data.get('p95_latency_ms')

        if not endpoint or p95_latency_ms is None:
            logger.error("Endpoint and latency must be provided.")
            return jsonify({"error": "Missing endpoint or latency"}), 400
        
        validate_latency_threshold(endpoint, p95_latency_ms)

        performance_thresholds[endpoint] = {'p95_latency_ms': p95_latency_ms}
        logger.info(f"Threshold configured for endpoint {endpoint}: p95 latency = {p95_latency_ms} ms")

        return jsonify({"message": "Threshold configured successfully"}), 200

    except ValueError as ve:
        logger.error(f"Invalid threshold value: {ve}")
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        logger.error(f"Error configuring threshold: {e}")
        return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    # Example data - replace with database integration in a real application
    performance_thresholds = {
        'api/users': {'p95_latency_ms': 200},
        'api/products': {'p95_latency_ms': 300}
    }
    app.run(debug=True)