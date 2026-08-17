from flask import Flask, jsonify, request
import logging
import threading
import time

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# In-memory storage for alerts (replace with a database in production)
alerts = []

# Mock metric values (replace with actual metric collection)
latency = 0.1  # seconds
error_rate = 0.01  # percentage
throughput = 1000  # requests per minute


def trigger_alert(message, severity):
    """Triggers an alert and adds it to the alerts list."""
    global alerts
    alerts.append({"message": message, "severity": severity})
    logging.warning(f"Alert triggered: {message} (Severity: {severity})")


def monitor_metrics():
    """Simulates metric monitoring and triggers alerts based on thresholds."""
    global latency, error_rate, throughput
    while True:
        # Simulate metric updates (replace with actual data)
        latency = 0.1 + (time.random() * 0.2)
        error_rate = 0.01 + (time.random() * 0.02)
        throughput = 1000 + int(time.random() * 500)

        # Trigger alerts based on thresholds
        if latency > 0.3:
            trigger_alert("High API Latency", "critical")
        if error_rate > 0.05:
            trigger_alert("High Error Rate", "major")
        if throughput < 500:
            trigger_alert("Low Throughput", "minor")

        time.sleep(10)  # Check metrics every 10 seconds


@app.route("/api-monitoring/metrics", methods=["GET"])
def get_metrics():
    """Exposes API metrics in JSON format."""
    global latency, error_rate, throughput
    metrics = {
        "latency": latency,
        "error_rate": error_rate,
        "throughput": throughput
    }
    return jsonify(metrics), 200


@app.route("/alerts/notifications", methods=["GET"])
def get_alerts():
    """Returns a list of active alerts."""
    global alerts
    # Return a copy to avoid modifying the original list directly
    alert_copy = alerts[:]  
    alerts = [] # clear alert list after returning, to prevent duplicates.
    return jsonify(alert_copy), 200


if __name__ == "__main__":
    # Start metric monitoring in a separate thread
    monitoring_thread = threading.Thread(target=monitor_metrics)
    monitoring_thread.daemon = True  # Allow the main program to exit even if this thread is running
    monitoring_thread.start()

    app.run(debug=False, host="0.0.0.0", port=5000)